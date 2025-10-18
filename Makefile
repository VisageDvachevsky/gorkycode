.PHONY: help

# ============================================
# AI-Tourist Professional Makefile (Helm Edition)
# ============================================

CHART_PATH := helm/ai-tourist
RELEASE_NAME := ai-tourist
NAMESPACE := ai-tourist
VALUES_FILE := $(CHART_PATH)/values.yaml
VALUES_DEV := $(CHART_PATH)/values-dev.yaml
VALUES_PROD := $(CHART_PATH)/values-prod.yaml

help:
	@echo "═══════════════════════════════════════════════════════"
	@echo "  AI-Tourist Gorkycode - Professional Helm Commands"
	@echo "═══════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 MONOLITH (Docker Compose):"
	@echo "  make dev-up          - Start monolith in dev mode"
	@echo "  make dev-down        - Stop monolith"
	@echo "  make dev-logs        - View monolith logs"
	@echo "  make dev-load-pois   - Load POI data in monolith"
	@echo ""
	@echo "☸️  KUBERNETES (Helm):"
	@echo "  make helm-install    - Install with Helm"
	@echo "  make helm-upgrade    - Upgrade release"
	@echo "  make helm-uninstall  - Uninstall release"
	@echo "  make helm-status     - Check deployment status"
	@echo "  make helm-logs       - View pod logs"
	@echo "  make helm-test       - Run Helm tests"
	@echo ""
	@echo "🏗️  BUILD & PUSH:"
	@echo "  make docker-build    - Build all images"
	@echo "  make docker-push     - Push images to registry"
	@echo ""
	@echo "🔧 DEVELOPMENT:"
	@echo "  make generate-protos - Generate gRPC code"
	@echo "  make gen-poi-cm      - Generate POI ConfigMap"
	@echo "  make format          - Format code"
	@echo "  make lint            - Lint code"
	@echo "  make test            - Run tests"
	@echo ""
	@echo "🐛 DEBUGGING:"
	@echo "  make debug-pod       - Shell into a pod"
	@echo "  make port-forward    - Forward API Gateway port"
	@echo "  make describe        - Describe all resources"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  make metrics         - View Prometheus metrics"
	@echo "  make grafana         - Open Grafana dashboard"

# ============================================
# MONOLITH (Docker Compose)
# ============================================

dev-up:
	@echo "🚀 Starting monolith in development mode..."
	docker compose up -d
	@echo ""
	@echo "✅ Monolith started!"
	@echo "   Frontend: http://localhost:5173"
	@echo "   API: http://localhost:8001"
	@echo ""
	@echo "⚠️  Don't forget to run: make dev-load-pois"

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

dev-logs-api:
	docker compose logs -f backend

dev-load-pois:
	@echo "📂 Loading POI data into monolith..."
	docker compose exec backend poetry run python scripts/load_pois.py
	@echo "✅ POI data loaded!"

dev-rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d

dev-clean:
	docker compose down -v
	docker system prune -f

# ============================================
# HELM DEPLOYMENT
# ============================================

helm-deps:
	@echo "📦 Installing Helm dependencies..."
	helm dependency update $(CHART_PATH)

helm-lint:
	@echo "🔍 Linting Helm chart..."
	helm lint $(CHART_PATH)

helm-template:
	@echo "🎨 Rendering Helm templates..."
	helm template $(RELEASE_NAME) $(CHART_PATH) \
		--namespace $(NAMESPACE) \
		--values $(VALUES_FILE)

helm-install: helm-deps helm-lint gen-poi-cm
	@echo "🚀 Installing AI-Tourist with Helm..."
	@if ! kubectl get namespace $(NAMESPACE) >/dev/null 2>&1; then \
		kubectl create namespace $(NAMESPACE); \
		echo "✓ Created namespace: $(NAMESPACE)"; \
	fi
	@echo ""
	@echo "⚙️  Deploying with Helm..."
	helm upgrade --install $(RELEASE_NAME) $(CHART_PATH) \
		--namespace $(NAMESPACE) \
		--values $(VALUES_FILE) \
		--create-namespace \
		--wait \
		--timeout 10m
	@echo ""
	@echo "✅ Deployment complete!"
	@echo ""
	@$(MAKE) helm-status

helm-upgrade: gen-poi-cm
	@echo "⬆️  Upgrading AI-Tourist release..."
	helm upgrade $(RELEASE_NAME) $(CHART_PATH) \
		--namespace $(NAMESPACE) \
		--values $(VALUES_FILE) \
		--wait \
		--timeout 10m
	@echo ""
	@echo "✅ Upgrade complete!"

helm-uninstall:
	@echo "🗑️  Uninstalling AI-Tourist..."
	helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE)
	@read -p "Delete namespace $(NAMESPACE)? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		kubectl delete namespace $(NAMESPACE); \
		echo "✓ Namespace deleted"; \
	fi

helm-status:
	@echo "📊 Deployment Status:"
	@echo ""
	@echo "═══ Helm Release ═══"
	helm status $(RELEASE_NAME) --namespace $(NAMESPACE)
	@echo ""
	@echo "═══ Pods ═══"
	kubectl get pods -n $(NAMESPACE) -o wide
	@echo ""
	@echo "═══ Services ═══"
	kubectl get services -n $(NAMESPACE)
	@echo ""
	@echo "═══ Jobs ═══"
	kubectl get jobs -n $(NAMESPACE)

helm-logs:
	@echo "📋 Pod Logs:"
	@read -p "Enter pod name (or press Enter for all): " pod; \
	if [ -z "$$pod" ]; then \
		kubectl logs -n $(NAMESPACE) --all-containers=true --tail=100 -l app.kubernetes.io/instance=$(RELEASE_NAME); \
	else \
		kubectl logs -n $(NAMESPACE) $$pod --tail=100 -f; \
	fi

helm-test:
	@echo "🧪 Running Helm tests..."
	helm test $(RELEASE_NAME) --namespace $(NAMESPACE)

# ============================================
# DOCKER BUILD & PUSH
# ============================================

REGISTRY ?= ghcr.io/your-org
TAG ?= latest

docker-build:
	@echo "🏗️  Building all Docker images..."
	@echo ""
	docker build -t $(REGISTRY)/ai-tourist-api-gateway:$(TAG) -f services/api-gateway/Dockerfile .
	docker build -t $(REGISTRY)/ai-tourist-embedding-service:$(TAG) -f services/embedding-service/Dockerfile .
	docker build -t $(REGISTRY)/ai-tourist-ranking-service:$(TAG) -f services/ranking-service/Dockerfile .
	docker build -t $(REGISTRY)/ai-tourist-route-planner-service:$(TAG) -f services/route-planner-service/Dockerfile .
	docker build -t $(REGISTRY)/ai-tourist-llm-service:$(TAG) -f services/llm-service/Dockerfile .
	docker build -t $(REGISTRY)/ai-tourist-geocoding-service:$(TAG) -f services/geocoding-service/Dockerfile .
	docker build -t $(REGISTRY)/ai-tourist-poi-service:$(TAG) -f services/poi-service/Dockerfile .
	docker build -t $(REGISTRY)/ai-tourist-frontend:$(TAG) -f frontend/Dockerfile .
	@echo ""
	@echo "✅ All images built!"

docker-push:
	@echo "📤 Pushing images to registry..."
	docker push $(REGISTRY)/ai-tourist-api-gateway:$(TAG)
	docker push $(REGISTRY)/ai-tourist-embedding-service:$(TAG)
	docker push $(REGISTRY)/ai-tourist-ranking-service:$(TAG)
	docker push $(REGISTRY)/ai-tourist-route-planner-service:$(TAG)
	docker push $(REGISTRY)/ai-tourist-llm-service:$(TAG)
	docker push $(REGISTRY)/ai-tourist-geocoding-service:$(TAG)
	docker push $(REGISTRY)/ai-tourist-poi-service:$(TAG)
	docker push $(REGISTRY)/ai-tourist-frontend:$(TAG)
	@echo "✅ All images pushed!"

docker-build-poi:
	@echo "🏗️  Building POI service..."
	docker build -t $(REGISTRY)/ai-tourist-poi-service:$(TAG) -f services/poi-service/Dockerfile .
	@echo "✅ POI service built!"

# ============================================
# DEVELOPMENT TOOLS
# ============================================

generate-protos:
	@echo "🔧 Generating gRPC code from proto files..."
	./scripts/generate-protos.sh
	@echo "✅ Proto generation complete!"

gen-poi-cm:
	@echo "📝 Generating POI data ConfigMap..."
	@if [ ! -f ./scripts/generate-poi-configmap.sh ]; then \
		echo "❌ Error: scripts/generate-poi-configmap.sh not found"; \
		exit 1; \
	fi
	chmod +x ./scripts/generate-poi-configmap.sh
	./scripts/generate-poi-configmap.sh
	@echo "✅ POI ConfigMap generated!"

format:
	@echo "🎨 Formatting Python code..."
	cd backend && poetry run black app/ || true
	cd backend && poetry run isort app/ || true
	@echo "✅ Code formatted!"

lint:
	@echo "🔍 Linting code..."
	cd backend && poetry run flake8 app/ || true
	cd backend && poetry run mypy app/ || true

test:
	@echo "🧪 Running tests..."
	cd backend && poetry run pytest -v

test-cov:
	@echo "🧪 Running tests with coverage..."
	cd backend && poetry run pytest --cov=app --cov-report=html

# ============================================
# DEBUGGING
# ============================================

debug-pod:
	@echo "🐚 Available pods:"
	@kubectl get pods -n $(NAMESPACE) | grep Running
	@echo ""
	@read -p "Enter pod name: " pod; \
	kubectl exec -it -n $(NAMESPACE) $$pod -- /bin/bash || \
	kubectl exec -it -n $(NAMESPACE) $$pod -- /bin/sh

port-forward:
	@echo "🔌 Setting up port forwarding..."
	@echo "   API Gateway will be available at http://localhost:8000"
	@API_POD=$$(kubectl get pods -n $(NAMESPACE) -l app.kubernetes.io/name=api-gateway -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -z "$$API_POD" ]; then \
		echo "❌ Error: API Gateway pod not found"; \
		exit 1; \
	fi; \
	echo "   Pod: $$API_POD"; \
	kubectl port-forward -n $(NAMESPACE) $$API_POD 8000:8000

describe:
	@echo "📝 Describing all resources..."
	kubectl describe all -n $(NAMESPACE)

top:
	@echo "📊 Resource usage:"
	kubectl top pods -n $(NAMESPACE)
	kubectl top nodes

# ============================================
# MONITORING
# ============================================

metrics:
	@echo "📊 Opening Prometheus..."
	@kubectl port-forward -n monitoring svc/prometheus 9090:9090 &
	@sleep 2
	@echo "✓ Prometheus available at http://localhost:9090"

grafana:
	@echo "📈 Opening Grafana..."
	@kubectl port-forward -n monitoring svc/grafana 3000:3000 &
	@sleep 2
	@echo "✓ Grafana available at http://localhost:3000"
	@echo "   Default credentials: admin/admin"

# ============================================
# DATABASE OPERATIONS
# ============================================

db-shell:
	@echo "🗄️  Connecting to PostgreSQL..."
	@POD=$$(kubectl get pods -n $(NAMESPACE) -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}'); \
	kubectl exec -it -n $(NAMESPACE) $$POD -- psql -U gorkycode -d gorkycode

db-backup:
	@echo "💾 Creating database backup..."
	@POD=$$(kubectl get pods -n $(NAMESPACE) -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}'); \
	kubectl exec -n $(NAMESPACE) $$POD -- pg_dump -U gorkycode gorkycode > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created!"

# ============================================
# CLEANUP
# ============================================

clean-all: helm-uninstall
	@echo "🧹 Cleaning up everything..."
	docker compose down -v
	docker system prune -af
	@echo "✅ Cleanup complete!"

# ============================================
# CI/CD HELPERS
# ============================================

ci-install:
	poetry install
	cd frontend && npm ci

ci-test:
	@$(MAKE) lint
	@$(MAKE) test

ci-build:
	@$(MAKE) docker-build

ci-deploy:
	@$(MAKE) helm-upgrade
