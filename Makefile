.PHONY: build deploy clean status logs test setup-ingress open

NAMESPACE := ai-tourist
INGRESS_HOST := ai-tourist.local

GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

all: build deploy test

setup-ingress:
	@echo "$(YELLOW)Enabling Ingress addon in Minikube...$(NC)"
	@minikube addons enable ingress
	@echo "$(GREEN)✅ Ingress addon enabled$(NC)"
	@sleep 5

build:
	@echo "$(YELLOW)Building Docker images...$(NC)"
	@eval $$(minikube docker-env) && \
	docker build -t ai-tourist-api-gateway:latest -f services/api-gateway/Dockerfile . && \
	docker build -t ai-tourist-embedding-service:latest -f services/embedding-service/Dockerfile . && \
	docker build -t ai-tourist-poi-service:latest -f services/poi-service/Dockerfile . && \
	docker build -t ai-tourist-ranking-service:latest -f services/ranking-service/Dockerfile . && \
	docker build -t ai-tourist-route-planner-service:latest -f services/route-planner-service/Dockerfile . && \
	docker build -t ai-tourist-llm-service:latest -f services/llm-service/Dockerfile . && \
	docker build -t ai-tourist-geocoding-service:latest -f services/geocoding-service/Dockerfile . && \
	docker build -t ai-tourist-frontend:latest frontend
	@echo "$(GREEN)✅ All images built successfully$(NC)"

deploy: setup-ingress
	@echo "$(YELLOW)Deploying to Kubernetes...$(NC)"
	@kubectl create namespace $(NAMESPACE) 2>/dev/null || true
	@helm upgrade --install ai-tourist helm/ai-tourist/ \
		-n $(NAMESPACE) \
		--wait \
		--timeout 10m \
		--set ingress.enabled=true \
		--set ingress.host=$(INGRESS_HOST)
	@echo "$(GREEN)✅ Deployment complete$(NC)"
	@echo ""
	@$(MAKE) status
	@echo ""
	@$(MAKE) show-url

show-url:
	@echo "$(GREEN)===========================================$(NC)"
	@echo "$(GREEN)   🚀 AI Tourist is ready!$(NC)"
	@echo "$(GREEN)===========================================$(NC)"
	@MINIKUBE_IP=$$(minikube ip); \
	echo ""; \
	echo "$(YELLOW)Add this to your /etc/hosts:$(NC)"; \
	echo "  $$MINIKUBE_IP $(INGRESS_HOST)"; \
	echo ""; \
	echo "$(YELLOW)Then open in browser:$(NC)"; \
	echo "  http://$(INGRESS_HOST)"; \
	echo ""; \
	echo "$(YELLOW)Or use port-forward (alternative):$(NC)"; \
	echo "  kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-frontend 8080:80"; \
	echo "  kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-api-gateway 8000:8000"; \
	echo "  Then open: http://localhost:8080"; \
	echo "$(GREEN)===========================================$(NC)"

open:
	@MINIKUBE_IP=$$(minikube ip); \
	echo "Opening http://$(INGRESS_HOST)..."; \
	echo "Make sure you added '$$MINIKUBE_IP $(INGRESS_HOST)' to /etc/hosts"; \
	xdg-open "http://$(INGRESS_HOST)" 2>/dev/null || echo "Please open http://$(INGRESS_HOST) manually"

status:
	@echo "$(YELLOW)Pod Status:$(NC)"
	@kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "$(YELLOW)Services:$(NC)"
	@kubectl get svc -n $(NAMESPACE)
	@echo ""
	@echo "$(YELLOW)Ingress:$(NC)"
	@kubectl get ingress -n $(NAMESPACE)

logs:
	@kubectl logs -n $(NAMESPACE) -l app=api-gateway -f --tail=50

test:
	@echo "$(YELLOW)Testing API endpoints...$(NC)"
	@sleep 10
	@echo ""
	@echo "$(YELLOW)1. Testing health endpoint...$(NC)"
	@kubectl run test-pod --rm -i --restart=Never --image=curlimages/curl -n $(NAMESPACE) -- \
		curl -s http://ai-tourist-api-gateway:8000/health | jq . || echo "Health check failed"
	@echo ""
	@echo "$(YELLOW)2. Testing readiness endpoint...$(NC)"
	@kubectl run test-pod --rm -i --restart=Never --image=curlimages/curl -n $(NAMESPACE) -- \
		curl -s http://ai-tourist-api-gateway:8000/ready | jq . || echo "Readiness check failed"
	@echo ""
	@echo "$(YELLOW)3. Testing categories endpoint...$(NC)"
	@kubectl run test-pod --rm -i --restart=Never --image=curlimages/curl -n $(NAMESPACE) -- \
		curl -s http://ai-tourist-api-gateway:8000/api/v1/categories/list | jq . || echo "Categories failed"
	@echo "$(GREEN)✅ Tests complete$(NC)"

clean:
	@echo "$(RED)Cleaning up...$(NC)"
	@helm uninstall ai-tourist -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete namespace $(NAMESPACE) --force --grace-period=0 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

restart: clean build deploy

help:
	@echo "$(GREEN)AI Tourist Makefile Commands:$(NC)"
	@echo ""
	@echo "  $(YELLOW)make build$(NC)        - Build all Docker images"
	@echo "  $(YELLOW)make deploy$(NC)       - Deploy to Kubernetes (includes setup-ingress)"
	@echo "  $(YELLOW)make all$(NC)          - Build + Deploy + Test"
	@echo "  $(YELLOW)make test$(NC)         - Run API tests"
	@echo "  $(YELLOW)make status$(NC)       - Show pod/service status"
	@echo "  $(YELLOW)make logs$(NC)         - Show API Gateway logs"
	@echo "  $(YELLOW)make show-url$(NC)     - Show access URLs"
	@echo "  $(YELLOW)make open$(NC)         - Open in browser (Linux/WSL)"
	@echo "  $(YELLOW)make clean$(NC)        - Remove deployment"
	@echo "  $(YELLOW)make restart$(NC)      - Clean + Build + Deploy"
	@echo ""
	@echo "$(YELLOW)Quick start:$(NC)"
	@echo "  git clone <repo>"
	@echo "  cd <repo>"
	@echo "  make all"
	@echo "  make show-url  # Follow instructions to add to /etc/hosts"