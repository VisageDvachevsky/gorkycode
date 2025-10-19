.PHONY: help build deploy clean logs load-pois status test-api port-forward full-deploy

# Configuration
NAMESPACE := ai-tourist
REGISTRY := 
DB_PASSWORD := secure_password_change_in_prod
DB_USER := aitourist
DB_NAME := aitourist_db
DB_HOST := localhost
DB_PORT := 5432

help:
	@echo "🚀 AI-Tourist Makefile Commands"
	@echo "================================"
	@echo ""
	@echo "Deployment:"
	@echo "  make full-deploy  - Complete deployment (build + deploy + load POIs)"
	@echo "  make build        - Build all Docker images"
	@echo "  make deploy       - Deploy to Kubernetes"
	@echo "  make clean        - Clean up everything"
	@echo ""
	@echo "Data:"
	@echo "  make load-pois    - Load POI data from ./data/poi.json"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status       - Show pod status"
	@echo "  make logs         - Show API gateway logs"
	@echo "  make test-api     - Test API endpoints"
	@echo "  make port-forward - Setup port forwarding"
	@echo ""

build:
	@echo "🏗️  Building Docker images..."
	@eval $$(minikube docker-env) && \
	docker build -t ai-tourist-api-gateway:latest -f services/api-gateway/Dockerfile . && \
	docker build -t ai-tourist-embedding-service:latest -f services/embedding-service/Dockerfile . && \
	docker build -t ai-tourist-poi-service:latest -f services/poi-service/Dockerfile . && \
	docker build -t ai-tourist-ranking-service:latest -f services/ranking-service/Dockerfile . && \
	docker build -t ai-tourist-route-planner-service:latest -f services/route-planner-service/Dockerfile . && \
	docker build -t ai-tourist-llm-service:latest -f services/llm-service/Dockerfile . && \
	docker build -t ai-tourist-geocoding-service:latest -f services/geocoding-service/Dockerfile . && \
	docker build -t ai-tourist-frontend:latest frontend
	@echo "✅ All images built successfully!"

deploy:
	@echo "🚀 Deploying to Kubernetes..."
	@kubectl create namespace $(NAMESPACE) 2>/dev/null || true
	@helm upgrade --install ai-tourist helm/ai-tourist/ \
		-n $(NAMESPACE) \
		--timeout 10m \
		--wait
	@echo "✅ Deployed successfully!"
	@echo ""
	@$(MAKE) status

clean:
	@echo "🧹 Cleaning up..."
	@helm uninstall ai-tourist -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete namespace $(NAMESPACE) --force --grace-period=0 2>/dev/null || true
	@echo "✅ Cleanup complete!"

status:
	@echo "📊 Pod Status:"
	@kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "📊 Service Status:"
	@kubectl get svc -n $(NAMESPACE)

logs:
	@echo "📋 API Gateway Logs:"
	@kubectl logs -n $(NAMESPACE) -l app=api-gateway -f

load-pois:
	@echo "📦 Loading POI data..."
	@if [ ! -f ./data/poi.json ]; then \
		echo "❌ Error: ./data/poi.json not found"; \
		exit 1; \
	fi
	@if [ ! -f ./scripts/load_pois.py ]; then \
		echo "❌ Error: ./scripts/load_pois.py not found"; \
		echo "Tip: Copy load_pois.py.fixed to scripts/load_pois.py"; \
		exit 1; \
	fi
	@echo "Setting up port-forward to database..."
	@kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-postgresql $(DB_PORT):5432 > /dev/null 2>&1 & \
	PF_PID=$$!; \
	sleep 3; \
	echo "Installing Python dependencies..."; \
	pip install asyncpg --break-system-packages --quiet 2>/dev/null || pip install asyncpg --quiet 2>/dev/null || true; \
	echo "Running POI loader..."; \
	DATABASE_URL="postgresql://$(DB_USER):$(DB_PASSWORD)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)" \
	python3 ./scripts/load_pois.py; \
	EXIT_CODE=$$?; \
	kill $$PF_PID 2>/dev/null || true; \
	if [ $$EXIT_CODE -eq 0 ]; then \
		echo "✅ POI data loaded successfully!"; \
	else \
		echo "❌ Failed to load POI data"; \
	fi; \
	exit $$EXIT_CODE

port-forward:
	@echo "🔌 Setting up port forwarding..."
	@echo "API Gateway: http://localhost:8000"
	@echo "Frontend: http://localhost:8080"
	@kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-api-gateway 8000:8000 > /dev/null 2>&1 & \
	kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-frontend 8080:80 > /dev/null 2>&1 &
	@sleep 2
	@echo "✅ Port forwarding active!"
	@echo ""
	@echo "Press Ctrl+C to stop, or run: pkill -f 'port-forward'"

test-api:
	@echo "🧪 Testing API endpoints..."
	@echo ""
	@echo "Setting up port-forward..."
	@kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-api-gateway 8000:8000 > /dev/null 2>&1 & \
	PF_PID=$$!; \
	sleep 2; \
	echo "Testing health endpoint..."; \
	curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Health check failed"; \
	echo ""; \
	echo "Testing categories endpoint..."; \
	curl -s http://localhost:8000/api/v1/categories/list | python3 -m json.tool || echo "❌ Categories check failed"; \
	echo ""; \
	kill $$PF_PID 2>/dev/null || true; \
	echo "✅ API tests complete!"

full-deploy: clean build deploy load-pois
	@echo ""
	@echo "✅ Full deployment complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  make test-api      - Test API endpoints"
	@echo "  make port-forward  - Access services locally"
	@echo "  make logs          - View logs"
	@echo ""
	@echo "Access the application:"
	@echo "  Frontend: kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-frontend 8080:80"
	@echo "  API:      kubectl port-forward -n $(NAMESPACE) svc/ai-tourist-api-gateway 8000:8000"