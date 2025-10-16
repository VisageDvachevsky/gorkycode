.PHONY: help k8s-install k8s-deploy k8s-stop k8s-clean dev-setup proto-gen docker-build-all

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
	@echo ""
	@echo "Kubernetes Management:"
	@echo "  make k8s-status     - Check cluster status"
	@echo "  make k8s-logs       - Show all service logs"
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
		sudo install minikube-linux-amd64 /usr/local/bin/minikube; }
	@command -v kubectl >/dev/null 2>&1 || { echo "Installing kubectl..."; \
		curl -LO "https://dl.k8s.io/release/$$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"; \
		sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl; }
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
	@eval $$(minikube docker-env --profile=$(CLUSTER_NAME)) && \
	echo "✓ Using minikube Docker daemon"
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
	@echo "  Frontend:  http://$$(minikube ip --profile=$(CLUSTER_NAME))"
	@echo "  API:       http://$$(minikube ip --profile=$(CLUSTER_NAME))/api"
	@echo "  Grafana:   http://$$(minikube ip --profile=$(CLUSTER_NAME)):3000 (admin/admin)"
	@echo "  Jaeger:    http://$$(minikube ip --profile=$(CLUSTER_NAME)):16686"
	@echo ""
	@echo "💡 Run 'make k8s-open' to open in browser"

k8s-open:
	@echo "🌐 Opening application..."
	@minikube service ingress-nginx-controller -n ingress-nginx --profile=$(CLUSTER_NAME) --url &
	@sleep 2
	@xdg-open http://$$(minikube ip --profile=$(CLUSTER_NAME)) 2>/dev/null || \
	 open http://$$(minikube ip --profile=$(CLUSTER_NAME)) 2>/dev/null || \
	 echo "Open http://$$(minikube ip --profile=$(CLUSTER_NAME)) in your browser"

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
	@kubectl logs -f -n $(NAMESPACE) -l app.kubernetes.io/instance=$(HELM_RELEASE) --all-containers=true --tail=100

k8s-load-pois:
	@echo "📦 Loading POIs to Kubernetes database..."
	@bash scripts/load-pois-to-k8s.sh

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
	pip install grpcio grpcio-tools poetry
	cd services/api-gateway && poetry install
	cd services/embedding-service && poetry install
	cd services/ranking-service && poetry install
	cd services/route-planner-service && poetry install
	cd services/llm-service && poetry install
	cd services/geocoding-service && poetry install
	cd services/poi-service && poetry install
	@echo "✅ Dev environment ready"

proto-gen:
	@echo "🔧 Generating gRPC code from proto files..."
	@./scripts/generate-protos.sh
	@echo "✅ Proto generation complete"

docker-build-all:
	@echo "🐳 Building all Docker images..."
	@eval $$(minikube docker-env --profile=$(CLUSTER_NAME))
	docker build -t ai-tourist/api-gateway:latest ./services/api-gateway
	docker build -t ai-tourist/embedding-service:latest ./services/embedding-service
	docker build -t ai-tourist/ranking-service:latest ./services/ranking-service
	docker build -t ai-tourist/route-planner-service:latest ./services/route-planner-service
	docker build -t ai-tourist/llm-service:latest ./services/llm-service
	docker build -t ai-tourist/geocoding-service:latest ./services/geocoding-service
	docker build -t ai-tourist/poi-service:latest ./services/poi-service
	docker build -t ai-tourist/frontend:latest ./frontend
	@echo "✅ All images built"

grafana:
	@echo "📊 Opening Grafana..."
	@xdg-open http://$$(minikube ip --profile=$(CLUSTER_NAME)):3000 2>/dev/null || \
	 echo "Open http://$$(minikube ip --profile=$(CLUSTER_NAME)):3000 (admin/admin)"

jaeger:
	@echo "🔍 Opening Jaeger..."
	@xdg-open http://$$(minikube ip --profile=$(CLUSTER_NAME)):16686 2>/dev/null || \
	 echo "Open http://$$(minikube ip --profile=$(CLUSTER_NAME)):16686"	