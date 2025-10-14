#!/bin/bash
set -e

echo "🔍 Checking Kubernetes cluster..."

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl."
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster"
    echo ""
    echo "💡 Quick setup options:"
    echo ""
    echo "   Option 1: Minikube (Local)"
    echo "   $ minikube start --cpus=4 --memory=8192"
    echo ""
    echo "   Option 2: Kind (Local)"
    echo "   $ kind create cluster --name aitourist"
    echo ""
    echo "   Option 3: Docker Desktop (Local)"
    echo "   Enable Kubernetes in Docker Desktop settings"
    echo ""
    exit 1
fi

echo "✅ Connected to cluster"
echo ""

CONTEXT=$(kubectl config current-context)
echo "📍 Current context: $CONTEXT"
echo ""

NODES=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
echo "🖥️  Nodes: $NODES"

if [ "$NODES" -eq 0 ]; then
    echo "⚠️  No nodes found in cluster"
    exit 1
fi

kubectl get nodes
echo ""

STORAGE_CLASSES=$(kubectl get storageclass --no-headers 2>/dev/null | wc -l)
if [ "$STORAGE_CLASSES" -eq 0 ]; then
    echo "⚠️  No storage classes found. PVCs may not work."
    echo "   For minikube, this is usually automatic."
    echo "   For Kind, you may need to install a storage provisioner."
else
    echo "💾 Storage classes available:"
    kubectl get storageclass
fi

echo ""

if ! kubectl get ingressclass &> /dev/null; then
    echo "⚠️  No ingress controller found"
    echo ""
    echo "💡 Install nginx ingress:"
    echo "   For minikube:"
    echo "   $ minikube addons enable ingress"
    echo ""
    echo "   For other clusters:"
    echo "   $ kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml"
    echo ""
else
    echo "🔌 Ingress controllers:"
    kubectl get ingressclass
fi

echo ""
echo "✅ Cluster is ready for deployment!"
echo ""
echo "💡 Next steps:"
echo "   1. Build images: make k8s-build"
echo "   2. Deploy: make k8s-apply"