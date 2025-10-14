#!/bin/bash
set -e

echo "🚀 Setting up local Kubernetes cluster..."
echo ""

if command -v minikube &> /dev/null; then
    echo "📦 Found Minikube"
    read -p "Use Minikube? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Starting Minikube..."
        minikube start --cpus=4 --memory=8192 --driver=docker
        
        echo ""
        echo "🔌 Enabling ingress..."
        minikube addons enable ingress
        
        echo ""
        echo "📊 Enabling metrics-server..."
        minikube addons enable metrics-server
        
        echo ""
        echo "✅ Minikube ready!"
        echo "   Dashboard: minikube dashboard"
        exit 0
    fi
fi

if command -v kind &> /dev/null; then
    echo "📦 Found Kind"
    read -p "Use Kind? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "Creating Kind cluster..."
        
        cat <<EOF | kind create cluster --name aitourist --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF
        
        echo ""
        echo "🔌 Installing nginx ingress..."
        kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
        
        echo ""
        echo "⏳ Waiting for ingress controller..."
        kubectl wait --namespace ingress-nginx \
          --for=condition=ready pod \
          --selector=app.kubernetes.io/component=controller \
          --timeout=90s
        
        echo ""
        echo "✅ Kind cluster ready!"
        exit 0
    fi
fi

echo "❌ No local Kubernetes tool found"
echo ""
echo "💡 Please install one of:"
echo "   - Minikube: https://minikube.sigs.k8s.io/docs/start/"
echo "   - Kind: https://kind.sigs.k8s.io/docs/user/quick-start/"
echo "   - Docker Desktop with Kubernetes enabled"
exit 1