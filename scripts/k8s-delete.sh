#!/bin/bash
set -e

echo "🗑️  Deleting Kubernetes resources..."

read -p "⚠️  This will delete all resources in 'aitourist' namespace. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🔌 Deleting Ingress..."
kubectl delete -f k8s/20-ingress.yaml --ignore-not-found=true

echo ""
echo "📊 Deleting Monitoring..."
kubectl delete -f k8s/30-monitoring.yaml --ignore-not-found=true

echo ""
echo "🎨 Deleting Frontend..."
kubectl delete -f k8s/14-frontend.yaml --ignore-not-found=true

echo ""
echo "🌐 Deleting Gateway..."
kubectl delete -f k8s/13-gateway.yaml --ignore-not-found=true

echo ""
echo "🧠 Deleting ML Service..."
kubectl delete -f k8s/12-ml-service.yaml --ignore-not-found=true

echo ""
echo "⚡ Deleting Redis..."
kubectl delete -f k8s/11-redis.yaml --ignore-not-found=true

echo ""
echo "🗄️  Deleting PostgreSQL..."
kubectl delete -f k8s/10-postgres.yaml --ignore-not-found=true

echo ""
echo "💾 Deleting PersistentVolumeClaims..."
kubectl delete -f k8s/03-pvc.yaml --ignore-not-found=true

echo ""
echo "🔐 Deleting Secrets..."
kubectl delete -f k8s/02-secrets.yaml --ignore-not-found=true

echo ""
echo "⚙️  Deleting ConfigMaps..."
kubectl delete -f k8s/01-configmap.yaml --ignore-not-found=true

echo ""
echo "📦 Deleting namespace..."
kubectl delete -f k8s/00-namespace.yaml --ignore-not-found=true

echo ""
echo "✅ All resources deleted!"