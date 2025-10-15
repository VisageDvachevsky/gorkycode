.PHONY: help setup build k8s-secrets k8s-build k8s-apply k8s-delete k8s-status k8s-logs k8s-restart k8s-port-stop k8s-port dev-up dev-down clean

help:
	@echo "🌍 AI Tourist - Kubernetes Deployment"
	@echo ""
	@echo "📋 Available commands:"
	@echo "  make setup              - Setup development environment"
	@echo "  make build              - Build all Docker images"
	@echo "  make k8s-apply          - Deploy to Kubernetes"
	@echo "  make k8s-status         - Check deployment status"
	@echo "  make k8s-port           - Port forward services (auto-cleanup)"
	@echo "  make k8s-port-stop      - Stop all port forwarding"
	@echo "  make k8s-logs           - View gateway logs"
	@echo "  make k8s-restart        - Restart all services"
	@echo "  make clean              - Clean up build artifacts"

setup:
	@echo "🔧 Setting up development environment..."
	@chmod +x scripts/*.sh 2>/dev/null || true
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Creating from template..."; \
		cp .env.example .env 2>/dev/null || echo "Please create .env manually"; \
	fi
	@mkdir -p k8s
	@echo "✅ Setup complete!"

build:
	@bash scripts/build-images.sh

k8s-secrets:
	@bash scripts/generate-k8s-secrets.sh

k8s-build: build

k8s-load-images:
	@bash scripts/load-images.sh

k8s-apply: k8s-secrets k8s-load-images
	@bash scripts/k8s-apply.sh

k8s-delete:
	@bash scripts/k8s-delete.sh

k8s-status:
	@echo "📊 Kubernetes Resources Status:"
	@echo ""
	@kubectl get all -n aitourist
	@echo ""
	@echo "💾 Persistent Volumes:"
	@kubectl get pvc -n aitourist
	@echo ""
	@echo "🔧 HPA Status:"
	@kubectl get hpa -n aitourist
	@echo ""
	@echo "📈 Resource Usage:"
	@kubectl top nodes 2>/dev/null || echo "⚠️  Metrics server not enabled"
	@kubectl top pods -n aitourist --sort-by=memory 2>/dev/null || true

k8s-logs:
	@echo "📝 Gateway logs (Ctrl+C to exit):"
	@kubectl logs -f -n aitourist -l app=gateway --tail=100

k8s-logs-ml:
	@echo "📝 ML Service logs (Ctrl+C to exit):"
	@kubectl logs -f -n aitourist -l app=ml-service --tail=100

k8s-logs-all:
	@echo "📝 All logs (Ctrl+C to exit):"
	@kubectl logs -f -n aitourist --all-containers=true --tail=50

k8s-restart:
	@echo "🔄 Restarting all services..."
	@kubectl rollout restart deployment -n aitourist
	@echo "✅ Restart initiated. Check status with: make k8s-status"

k8s-port-stop:
	@echo "🛑 Stopping port forwarding..."
	@killall kubectl 2>/dev/null || true
	@sudo kill -9 $$(sudo lsof -t -i:8000) 2>/dev/null || true
	@sudo kill -9 $$(sudo lsof -t -i:3000) 2>/dev/null || true
	@sudo kill -9 $$(sudo lsof -t -i:3001) 2>/dev/null || true
	@sleep 1
	@echo "✅ Port forwarding stopped"

k8s-port: k8s-port-stop
	@echo "🔌 Starting port forwarding..."
	@echo "   Gateway API: http://localhost:8000"
	@echo "   Frontend:    http://localhost:3000"
	@echo "   Grafana:     http://localhost:3001"
	@echo ""
	@echo "⏳ Waiting for services..."
	@kubectl wait --for=condition=ready pod -l app=gateway -n aitourist --timeout=60s || true
	@kubectl port-forward -n aitourist svc/gateway 8000:8000 > /dev/null 2>&1 & \
	kubectl port-forward -n aitourist svc/frontend 3000:80 > /dev/null 2>&1 & \
	kubectl port-forward -n aitourist svc/grafana 3001:3000 > /dev/null 2>&1 & \
	sleep 3 && \
	echo "" && \
	echo "✅ Port forwarding active!" && \
	echo "" && \
	echo "📖 API Documentation: http://localhost:8000/docs" && \
	echo "🎨 Frontend App:      http://localhost:3000" && \
	echo "📊 Grafana:           http://localhost:3001" && \
	echo "" && \
	echo "Press Ctrl+C to stop (or run: make k8s-port-stop)" && \
	wait

k8s-shell-gateway:
	@kubectl exec -it -n aitourist deployment/gateway -- /bin/bash

k8s-shell-ml:
	@kubectl exec -it -n aitourist deployment/ml-service -- /bin/bash

k8s-db-psql:
	@kubectl exec -it -n aitourist deployment/postgres -- psql -U postgres -d aitourist

dev-up:
	@echo "🚀 Starting development environment..."
	@docker-compose up -d
	@echo "✅ Dev environment running!"
	@echo "   Gateway: http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"

dev-down:
	@echo "🛑 Stopping development environment..."
	@docker-compose down
	@echo "✅ Dev environment stopped"

dev-logs:
	@docker-compose logs -f

clean:
	@echo "🧹 Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@rm -f k8s/02-secrets.yaml
	@rm -f .k8s-config
	@docker system prune -f
	@echo "✅ Clean complete!"

k8s-full-deploy: setup k8s-build k8s-apply
	@echo ""
	@echo "🎉 Full deployment complete!"
	@echo ""
	@echo "💡 Next steps:"
	@echo "   make k8s-status    - Check status"
	@echo "   make k8s-port      - Access services"
	@echo "   make k8s-logs      - View logs"
