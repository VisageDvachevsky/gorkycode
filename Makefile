.PHONY: help build deploy clean logs fix

help:
	@echo "Available commands:"
	@echo "  make build   - Build all Docker images"
	@echo "  make deploy  - Deploy to Kubernetes"
	@echo "  make clean   - Clean up deployments"
	@echo "  make logs    - Show api-gateway logs"
	@echo "  make fix     - Apply fixes and redeploy"

build:
	@echo "🏗️  Building all images..."
	@docker build -t ai-tourist/api-gateway:latest -f services/api-gateway/Dockerfile .
	@docker build -t ai-tourist/embedding-service:latest -f services/embedding-service/Dockerfile .
	@docker build -t ai-tourist/poi-service:latest -f services/poi-service/Dockerfile .
	@docker build -t ai-tourist/ranking-service:latest -f services/ranking-service/Dockerfile .
	@docker build -t ai-tourist/route-planner-service:latest -f services/route-planner-service/Dockerfile .
	@docker build -t ai-tourist/llm-service:latest -f services/llm-service/Dockerfile .
	@docker build -t ai-tourist/geocoding-service:latest -f services/geocoding-service/Dockerfile .
	@docker build -t ai-tourist/frontend:latest frontend
	@echo "✅ All images built!"

deploy:
	@echo "🚀 Deploying to Kubernetes..."
	@kubectl create namespace ai-tourist || true
	@helm upgrade --install ai-tourist helm/ai-tourist/ -n ai-tourist
	@echo "✅ Deployed!"

clean:
	@echo "🧹 Cleaning up..."
	@helm uninstall ai-tourist -n ai-tourist || true
	@kubectl delete namespace ai-tourist || true
	@echo "✅ Cleaned!"

logs:
	@kubectl logs -n ai-tourist -l app=api-gateway -f

fix:
	@echo "🔧 Applying fixes..."
	@eval $$(minikube docker-env) && make build
	@kubectl rollout restart deployment -n ai-tourist
	@echo "⏳ Waiting for pods..."
	@kubectl wait --for=condition=ready pod -l app=api-gateway -n ai-tourist --timeout=120s || true
	@echo "✅ Fix applied! Check status:"
	@kubectl get pods -n ai-tourist