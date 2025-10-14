#!/bin/bash
set -e

echo "🚀 Deploying to Kubernetes..."

if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Error: Kubernetes cluster not accessible"
    echo "   Make sure kubectl is configured and cluster is running"
    exit 1
fi

echo ""
echo "📦 Creating namespace..."
kubectl apply -f k8s/00-namespace.yaml

echo ""
echo "⚙️  Creating ConfigMaps..."
kubectl apply -f k8s/01-configmap.yaml

echo ""
echo "🔐 Creating Secrets..."
if [ ! -f k8s/02-secrets.yaml ]; then
    echo "⚠️  Secrets file not found. Generating from .env..."
    bash scripts/generate-k8s-secrets.sh
fi
kubectl apply -f k8s/02-secrets.yaml

echo ""
echo "💾 Creating PersistentVolumeClaims..."
kubectl apply -f k8s/03-pvc.yaml

echo ""
echo "🗄️  Creating database init scripts..."
kubectl apply -f k8s/04-db-init.yaml

echo ""
echo "🔐 Creating Network Policies..."
kubectl apply -f k8s/05-network-policy.yaml

echo ""
echo "🛡️  Creating Pod Disruption Budgets..."
kubectl apply -f k8s/06-pod-disruption-budget.yaml

echo ""
echo "👤 Creating RBAC..."
kubectl apply -f k8s/07-rbac.yaml

echo ""
echo "🗄️  Deploying PostgreSQL..."
kubectl apply -f k8s/10-postgres.yaml

echo ""
echo "⚡ Deploying Redis..."
kubectl apply -f k8s/11-redis.yaml

echo ""
echo "🧠 Deploying ML Service..."
kubectl apply -f k8s/12-ml-service.yaml

echo ""
echo "🌐 Deploying Gateway (API)..."
kubectl apply -f k8s/13-gateway.yaml

echo ""
echo "🎨 Deploying Frontend..."
kubectl apply -f k8s/14-frontend.yaml

echo ""
echo "🔌 Creating Ingress..."
kubectl apply -f k8s/20-ingress.yaml

if [ -f k8s/30-monitoring.yaml ]; then
    echo ""
    echo "📊 Deploying Monitoring (Prometheus + Grafana)..."
    kubectl apply -f k8s/30-monitoring.yaml
    
    if [ -f k8s/31-servicemonitor.yaml ]; then
        echo ""
        echo "📈 Creating ServiceMonitors..."
        kubectl apply -f k8s/31-servicemonitor.yaml || echo "⚠️  ServiceMonitor CRD not installed (skip if not using Prometheus Operator)"
    fi
fi

if [ -f k8s/40-backup.yaml ]; then
    echo ""
    echo "💾 Setting up database backups..."
    kubectl apply -f k8s/40-backup.yaml
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Checking deployment status..."
kubectl get pods -n aitourist

echo ""
echo "💡 Useful commands:"
echo "   Check status: kubectl get all -n aitourist"
echo "   View logs: kubectl logs -f -n aitourist -l app=gateway"
echo "   Port forward: kubectl port-forward -n aitourist svc/gateway 8000:8000"
echo "   Access app: http://localhost:8000 (after port-forward)"