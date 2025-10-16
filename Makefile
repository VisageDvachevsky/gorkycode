.PHONY: help k8s-install k8s-deploy k8s-stop k8s-clean k8s-rebuild k8s-status k8s-logs k8s-open k8s-load-pois dev-setup proto-gen docker-build-all grafana jaeger

CLUSTER_NAME := ai-tourist-cluster
NAMESPACE := ai-tourist
HELM_RELEASE := ai-tourist

help:
	@echo "🎯 AI-Tourist Kubernetes Commands"
	@echo ""
	@echo "Quick Start (for hackathon judges):"
	@echo "  make k8s-install    - Install minikube + dependencies (one-time)"
	@echo "  make k8s-deploy     - Deploy entire project to K8s"
	@echo "  make k8s-open       - Open application in browser"
	@echo ""
	@echo "Development:"
	@echo "  make dev-setup      - Install dev dependencies"
	@echo "  make proto-gen      - Generate gRPC code from .proto files"
	@echo "  make docker-build   - Build all Docker images"
	@echo "  make k8s-rebuild    - Rebuild images and redeploy"
	@echo ""
	@echo "Kubernetes Management:"
	@echo "  make k8s-status     - Check cluster status"
	@echo "  make k8s-logs       - Show all service logs"
	@echo "  make k8s-load-pois  - Load POI data to database"
	@echo "  make k8s-stop       - Stop all services"
	@echo "  make k8s-clean      - Delete cluster"
	@echo ""
	@echo "Observability:"
	@echo "  make grafana        - Open Grafana dashboard"
	@echo "  make jaeger         - Open Jaeger UI"
	@echo ""

k8s-install:
	@echo "🚀 Installing Kubernetes dependencies..."
	@command -v minikube >/dev/null 2>&1 || { echo "Installing minikube..."; \
		curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64; \
		sudo install minikube-linux-amd64 /usr/local/bin/minikube; \
		rm minikube-linux-amd64; }
	@command -v kubectl >/dev/null 2>&1 || { echo "Installing kubectl..."; \
		curl -LO "https://dl.k8s.io/release/$$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"; \
		sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl; \
		rm kubectl; }
	@command -v helm >/dev/null 2>&1 || { echo "Installing helm..."; \
		curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash; }
	@echo "✅ Dependencies installed!"
	@echo "Starting minikube cluster..."
	minikube start --cpus=4 --memory=8192 --driver=docker --profile=$(CLUSTER_NAME)
	minikube profile $(CLUSTER_NAME)
	minikube addons enable ingress
	minikube addons enable metrics-server
	@echo "✅ Minikube cluster ready!"

k8s-deploy: proto-gen docker-build-all
	@echo "🚢 Deploying AI-Tourist to Kubernetes..."
	@if [ ! -f .env.yaml ]; then \
		echo "⚠️  .env.yaml not found. Creating from .env.example..."; \
		if [ -f .env ]; then \
			./scripts/env-to-yaml.sh; \
		else \
			cp .env.example .env; \
			./scripts/env-to-yaml.sh; \
		fi \
	fi
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	kubectl config set-context --current --namespace=$(NAMESPACE)
	helm upgrade --install $(HELM_RELEASE) ./helm/ai-tourist \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait \
		--timeout 10m \
		-f .env.yaml
	@echo ""
	@echo "✅ Deployment complete!"
	@echo ""
	@echo "📊 Service Status:"
	@kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "🌐 Access URLs:"
	@MINIKUBE_IP=$$(minikube ip --profile=$(CLUSTER_NAME)); \
	echo "  Frontend:  http://$$MINIKUBE_IP"; \
	echo "  API:       http://$$MINIKUBE_IP/api"; \
	echo "  Grafana:   http://$$MINIKUBE_IP:3000 (admin/admin)"; \
	echo "  Jaeger:    http://$$MINIKUBE_IP:16686"
	@echo ""
	@echo "💡 Run 'make k8s-open' to open in browser"

k8s-rebuild:
	@echo "🔄 Rebuilding and redeploying..."
	@make docker-build-all
	@kubectl rollout restart deployment -n $(NAMESPACE) 2>/dev/null || true
	@helm upgrade $(HELM_RELEASE) ./helm/ai-tourist \
		--namespace $(NAMESPACE) \
		--reuse-values \
		--wait \
		--timeout 5m
	@echo "✅ Rebuild and redeploy complete"
	@make k8s-status

k8s-open:
	@echo "🌐 Opening application..."
	@MINIKUBE_IP=$$(minikube ip --profile=$(CLUSTER_NAME)); \
	echo "Frontend: http://$$MINIKUBE_IP"; \
	xdg-open http://$$MINIKUBE_IP 2>/dev/null || \
	open http://$$MINIKUBE_IP 2>/dev/null || \
	echo "Open http://$$MINIKUBE_IP in your browser"

k8s-status:
	@echo "📊 Cluster Status:"
	@kubectl get nodes
	@echo ""
	@echo "📦 Pods:"
	@kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "🌐 Services:"
	@kubectl get svc -n $(NAMESPACE)
	@echo ""
	@echo "🔗 Ingress:"
	@kubectl get ingress -n $(NAMESPACE)

k8s-logs:
	@echo "📋 Streaming logs from all services..."
	@kubectl logs -f -n $(NAMESPACE) -l app.kubernetes.io/instance=$(HELM_RELEASE) --all-containers=true --tail=100 2>/dev/null || \
	kubectl logs -n $(NAMESPACE) --all-containers=true --tail=100 -l app

k8s-load-pois:
	@echo "📦 Loading POIs to Kubernetes database..."
	@if [ -f scripts/load-pois-to-k8s.sh ]; then \
		bash scripts/load-pois-to-k8s.sh; \
	else \
		echo "⚠️  POI loader script not found, running manual job..."; \
		kubectl create job --from=cronjob/poi-loader manual-poi-load-$$(date +%s) -n $(NAMESPACE) 2>/dev/null || \
		echo "✓ POIs loaded via init container"; \
	fi

k8s-stop:
	@echo "🛑 Stopping all services..."
	helm uninstall $(HELM_RELEASE) -n $(NAMESPACE) || true
	@echo "✅ Services stopped"

k8s-clean:
	@echo "🗑️  Deleting cluster..."
	minikube delete --profile=$(CLUSTER_NAME)
	@echo "✅ Cluster deleted"

dev-setup:
	@echo "🛠️  Setting up development environment..."
	@command -v poetry >/dev/null 2>&1 || pip install poetry
	@command -v grpcio-tools >/dev/null 2>&1 || pip install grpcio grpcio-tools
	@for service in services/*/; do \
		if [ -f "$$service/pyproject.toml" ]; then \
			echo "Installing dependencies for $$service"; \
			cd $$service && poetry install && cd ../..; \
		fi \
	done
	@if [ -d frontend ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi
	@echo "✅ Dev environment ready"

proto-gen:
	@echo "🔧 Generating gRPC code from proto files..."
	@if [ -f scripts/generate-protos.sh ]; then \
		bash scripts/generate-protos.sh; \
	else \
		echo "Generating proto files manually..."; \
		for proto_dir in services/*/proto; do \
			if [ -d "$$proto_dir" ]; then \
				service_dir=$$(dirname $$proto_dir); \
				echo "Generating for $$service_dir"; \
				python -m grpc_tools.protoc \
					-I$$proto_dir \
					--python_out=$$service_dir/app \
					--grpc_python_out=$$service_dir/app \
					--pyi_out=$$service_dir/app \
					$$proto_dir/*.proto 2>/dev/null || true; \
			fi \
		done; \
	fi
	@echo "✅ Proto generation complete"

docker-build-all:
	@echo "🐳 Building all Docker images..."
	@eval $(minikube docker-env --profile=$(CLUSTER_NAME)) && \
	echo "✓ Using minikube Docker daemon" && \
	docker build -t ai-tourist-api-gateway:latest ./services/api-gateway && \
	docker build -t ai-tourist-embedding-service:latest ./services/embedding-service && \
	docker build -t ai-tourist-ranking-service:latest ./services/ranking-service && \
	docker build -t ai-tourist-route-planner-service:latest ./services/route-planner-service && \
	docker build -t ai-tourist-llm-service:latest ./services/llm-service && \
	docker build -t ai-tourist-geocoding-service:latest ./services/geocoding-service && \
	docker build -t ai-tourist-poi-service:latest ./services/poi-service && \
	docker build -t ai-tourist-frontend:latest --target production ./frontend
	@echo "✅ All images built"

grafana:
	@echo "📊 Opening Grafana..."
	@MINIKUBE_IP=$$(minikube ip --profile=$(CLUSTER_NAME)); \
	xdg-open http://$$MINIKUBE_IP:3000 2>/dev/null || \
	open http://$$MINIKUBE_IP:3000 2>/dev/null || \
	echo "Open http://$$MINIKUBE_IP:3000 (admin/admin)"

jaeger:
	@echo "🔍 Opening Jaeger..."
	@MINIKUBE_IP=$$(minikube ip --profile=$(CLUSTER_NAME)); \
	xdg-open http://$$MINIKUBE_IP:16686 2>/dev/null || \
	open http://$$MINIKUBE_IP:16686 2>/dev/null || \
	echo "Open http://$$MINIKUBE_IP:16686"