.PHONY: help setup build k8s-secrets k8s-build k8s-apply k8s-delete k8s-status k8s-logs k8s-restart dev-up dev-down clean check-structure fix-structure quickfix fix-frontend

help:
	@echo "🌍 AI Tourist - Kubernetes Deployment"
	@echo ""
	@echo "📋 Available commands:"
	@echo "  make check-structure    - Check project structure"
	@echo "  make quickfix           - Interactive setup for your structure"
	@echo "  make fix-frontend       - Fix frontend TypeScript errors"
	@echo "  make fix-structure      - Auto-fix project structure"
	@echo "  make setup              - Setup development environment"
	@echo "  make build              - Build all Docker images"
	@echo "  make k8s-secrets        - Generate k8s secrets from .env"
	@echo "  make k8s-build          - Build Docker images for k8s"
	@echo "  make k8s-load-images    - Load images into k8s cluster"
	@echo "  make k8s-apply          - Deploy to Kubernetes"
	@echo "  make k8s-delete         - Delete all k8s resources"
	@echo "  make k8s-status         - Check deployment status"
	@echo "  make k8s-logs           - View gateway logs"
	@echo "  make k8s-restart        - Restart all services"
	@echo "  make k8s-port           - Port forward services"
	@echo "  make dev-up             - Start dev environment (docker-compose)"
	@echo "  make dev-down           - Stop dev environment"
	@echo "  make clean              - Clean up build artifacts"

check-structure:
	@bash scripts/check-structure.sh

quickfix:
	@bash scripts/quickfix.sh

fix-frontend:
	@bash scripts/fix-frontend-wizard.sh

fix-structure:
	@bash scripts/fix-structure.sh

setup: check-structure
	@echo "🔧 Setting up development environment..."
	@chmod +x scripts/*.sh 2>/dev/null || true
	@if [ ! -f .env ]; then \
		echo "⚠️  .env file not found. Creating from template..."; \
		cp .env.example .env 2>/dev/null || echo "Please create .env manually"; \
	fi
	@mkdir -p k8s
	@echo "✅ Setup complete!"
	@echo ""
	@echo "📂 Project structure detected:"
	@bash scripts/check-structure.sh | grep "✅" || echo "⚠️  Run 'make quickfix' to configure"

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
	@echo "💾 Storage:"
	@kubectl get pvc -n aitourist
	@echo ""
	@echo "🔌 Ingress:"
	@kubectl get ingress -n aitourist

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

k8s-port:
	@echo "🔌 Port forwarding services..."
	@echo "   Gateway: http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Grafana: http://localhost:3001"
	@echo ""
	@echo "Press Ctrl+C to stop port forwarding"
	@kubectl port-forward -n aitourist svc/gateway 8000:8000 & \
	kubectl port-forward -n aitourist svc/frontend 3000:80 & \
	kubectl port-forward -n aitourist svc/grafana 3001:3000 & \
	wait

k8s-shell-gateway:
	@kubectl exec -it -n aitourist deployment/gateway -- /bin/bash

k8s-shell-ml:
	@kubectl exec -it -n aitourist deployment/ml-service -- /bin/bash

k8s-db-psql:
	@kubectl exec -it -n aitourist deployment/postgres -- psql -U postgres -d aitourist

dev-up:
	@echo "🚀 Starting development environment..."
	@docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Dev environment running!"
	@echo "   Gateway: http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"

dev-down:
	@echo "🛑 Stopping development environment..."
	@docker-compose -f docker-compose.dev.yml down
	@echo "✅ Dev environment stopped"

dev-logs:
	@docker-compose -f docker-compose.dev.yml logs -f

clean:
	@echo "🧹 Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@rm -f k8s/02-secrets.yaml
	@rm -f .k8s-config
	@echo "✅ Clean complete!"

k8s-full-deploy: check-structure fix-structure setup k8s-build k8s-apply k8s-status
	@echo ""
	@echo "🎉 Full deployment complete!"
	@echo ""
	@echo "💡 Next steps:"
	@echo "   1. Port forward: make k8s-port"
	@echo "   2. Access app: http://localhost:3000"
	@echo "   3. View logs: make k8s-logs"
	@echo ""
	@echo "Or use the one-command script:"
	@echo "   bash deploy.sh"

k8s-redeploy: k8s-delete k8s-full-deploy

one-click-deploy:
	@chmod +x deploy.sh
	@./deploy.sh