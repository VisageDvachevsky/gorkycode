.PHONY: build deploy clean status logs

NAMESPACE := ai-tourist

build:
	@echo "Building images..."
	@eval $$(minikube docker-env) && \
	docker build -t ai-tourist-api-gateway:latest -f services/api-gateway/Dockerfile . && \
	docker build -t ai-tourist-embedding-service:latest -f services/embedding-service/Dockerfile . && \
	docker build -t ai-tourist-poi-service:latest -f services/poi-service/Dockerfile . && \
	docker build -t ai-tourist-ranking-service:latest -f services/ranking-service/Dockerfile . && \
	docker build -t ai-tourist-route-planner-service:latest -f services/route-planner-service/Dockerfile . && \
	docker build -t ai-tourist-llm-service:latest -f services/llm-service/Dockerfile . && \
	docker build -t ai-tourist-geocoding-service:latest -f services/geocoding-service/Dockerfile . && \
	docker build -t ai-tourist-frontend:latest frontend
	@echo "✅ Done"

deploy:
	@echo "Deploying..."
	@kubectl create namespace $(NAMESPACE) 2>/dev/null || true
	@helm upgrade --install ai-tourist helm/ai-tourist/ -n $(NAMESPACE) --wait --timeout 10m
	@echo "✅ Deployed"

clean:
	@helm uninstall ai-tourist -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete namespace $(NAMESPACE) --force --grace-period=0 2>/dev/null || true

status:
	@kubectl get pods -n $(NAMESPACE)

logs:
	@kubectl logs -n $(NAMESPACE) -l app=api-gateway -f
