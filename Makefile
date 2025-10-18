.PHONY: help deploy clean build status logs dashboard

# ============================================
# AI-Tourist Makefile - Senior DevOps Edition
# ============================================

help:
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  AI-Tourist Deployment Commands"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "🚀 DEPLOYMENT:"
	@echo "  make deploy          - Deploy to minikube (build + install)"
	@echo "  make deploy-fast     - Deploy without building images"
	@echo "  make deploy-clean    - Clean deploy (remove old + deploy)"
	@echo ""
	@echo "🏗️  BUILD:"
	@echo "  make build           - Build all Docker images"
	@echo "  make build-service   - Build specific service (SERVICE=name)"
	@echo ""
	@echo "🔧 MANAGEMENT:"
	@echo "  make status          - Show deployment status"
	@echo "  make logs            - Show logs (SERVICE=name optional)"
	@echo "  make clean           - Remove deployment"
	@echo "  make restart         - Restart all pods"
	@echo ""
	@echo "🐛 DEBUG:"
	@echo "  make shell           - Shell into pod (POD=name)"
	@echo "  make describe        - Describe resources"
	@echo "  make events          - Show cluster events"
	@echo "  make dashboard       - Open Kubernetes dashboard"
	@echo ""
	@echo "📊 MONITORING:"
	@echo "  make port-forward    - Setup port forwarding"
	@echo "  make top             - Show resource usage"
	@echo ""

# ============================================
# DEPLOYMENT
# ============================================

deploy:
	@echo "🚀 Deploying AI-Tourist..."
	@chmod +x deploy.sh
	@./deploy.sh

deploy-fast:
	@echo "⚡ Fast deploy (no build)..."
	@chmod +x deploy.sh
	@./deploy.sh --no-build

deploy-clean:
	@echo "🧹 Clean deploy..."
	@chmod +x deploy.sh
	@./deploy.sh --clean

# ============================================
# BUILD
# ============================================

build:
	@echo "🏗️  Building all images..."
	@eval $$(minikube docker-env) && \
	docker build -t gorkycode/frontend:latest -f frontend/Dockerfile . && \
	docker build -t gorkycode/api-gateway:latest -f services/api-gateway/Dockerfile . && \
	docker build -t gorkycode/embedding-service:latest -f services/embedding-service/Dockerfile . && \
	docker build -t gorkycode/ranking-service:latest -f services/ranking-service/Dockerfile . && \
	docker build -t gorkycode/route-planner-service:latest -f services/route-planner-service/Dockerfile . && \
	docker build -t gorkycode/llm-service:latest -f services/llm-service/Dockerfile . && \
	docker build -t gorkycode/geocoding-service:latest -f services/geocoding-service/Dockerfile . && \
	docker build -t gorkycode/poi-service:latest -f services/poi-service/Dockerfile .
	@echo "✅ All images built!"

build-service:
ifndef SERVICE
	@echo "❌ Error: SERVICE not specified"
	@echo "Usage: make build-service SERVICE=api-gateway"
	@exit 1
endif
	@echo "🏗️  Building $(SERVICE)..."
	@eval $$(minikube docker-env) && \
	if [ "$(SERVICE)" = "frontend" ]; then \
		docker build -t gorkycode/frontend:latest -f frontend/Dockerfile .; \
	else \
		docker build -t gorkycode/$(SERVICE):latest -f services/$(SERVICE)/Dockerfile .; \
	fi
	@echo "✅ $(SERVICE) built!"

# ============================================
# MANAGEMENT
# ============================================

status:
	@echo "📊 Deployment Status"
	@echo "════════════════════"
	@echo ""
	@echo "Pods:"
	@kubectl get pods -n ai-tourist
	@echo ""
	@echo "Services:"
	@kubectl get services -n ai-tourist
	@echo ""
	@echo "Deployments:"
	@kubectl get deployments -n ai-tourist

logs:
ifdef SERVICE
	@echo "📋 Logs for $(SERVICE):"
	@kubectl logs -n ai-tourist -l app=$(SERVICE) --tail=100 -f
else
	@echo "📋 All logs (last 50 lines):"
	@kubectl logs -n ai-tourist --all-containers=true --tail=50
endif

clean:
	@echo "🧹 Cleaning up..."
	@helm uninstall ai-tourist -n ai-tourist 2>/dev/null || true
	@kubectl delete namespace ai-tourist --ignore-not-found=true
	@echo "✅ Cleanup complete"

restart:
	@echo "🔄 Restarting all pods..."
	@kubectl rollout restart deployment -n ai-tourist
	@echo "✅ Restart initiated"

# ============================================
# DEBUG
# ============================================

shell:
ifndef POD
	@echo "Available pods:"
	@kubectl get pods -n ai-tourist
	@echo ""
	@echo "Usage: make shell POD=<pod-name>"
else
	@kubectl exec -it -n ai-tourist $(POD) -- /bin/bash || \
	kubectl exec -it -n ai-tourist $(POD) -- /bin/sh
endif

describe:
	@echo "📝 Describing resources..."
	@kubectl describe all -n ai-tourist

events:
	@echo "📅 Recent events:"
	@kubectl get events -n ai-tourist --sort-by='.lastTimestamp'

dashboard:
	@echo "📊 Opening Kubernetes dashboard..."
	@minikube dashboard

# ============================================
# MONITORING
# ============================================

port-forward:
	@echo "🔌 Setting up port forwarding..."
	@pkill -f "kubectl port-forward" 2>/dev/null || true
	@kubectl port-forward -n ai-tourist svc/ai-tourist-api-gateway 8000:8000 &
	@kubectl port-forward -n ai-tourist svc/ai-tourist-frontend 3000:80 &
	@sleep 2
	@echo "✅ Port forwarding active:"
	@echo "   Frontend: http://localhost:3000"
	@echo "   API:      http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

top:
	@echo "📊 Resource usage:"
	@kubectl top pods -n ai-tourist
	@echo ""
	@kubectl top nodes

# ============================================
# HELPERS
# ============================================

helm-template:
	@echo "🎨 Rendering Helm templates..."
	@helm template ai-tourist helm/ai-tourist \
		--namespace ai-tourist \
		--values helm/ai-tourist/values.yaml \
		--values helm/ai-tourist/values-dev.yaml

helm-lint:
	@echo "🔍 Linting Helm chart..."
	@helm lint helm/ai-tourist

minikube-start:
	@echo "🚀 Starting minikube..."
	@minikube start --cpus=4 --memory=8192 --driver=docker
	@minikube addons enable ingress
	@minikube addons enable metrics-server

minikube-stop:
	@echo "🛑 Stopping minikube..."
	@minikube stop

minikube-delete:
	@echo "🗑️  Deleting minikube cluster..."
	@minikube delete
