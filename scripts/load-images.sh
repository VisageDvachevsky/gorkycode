#!/bin/bash
set -e

echo "📦 Loading Docker images into Kubernetes cluster..."
echo ""

# Detect cluster type
CLUSTER_TYPE=""

if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    CLUSTER_TYPE="minikube"
    echo "✅ Detected Minikube cluster"
elif command -v kind &> /dev/null && kind get clusters 2>/dev/null | grep -q .; then
    CLUSTER_TYPE="kind"
    CLUSTER_NAME=$(kind get clusters | head -1)
    echo "✅ Detected Kind cluster: $CLUSTER_NAME"
elif kubectl config current-context | grep -q "docker-desktop"; then
    CLUSTER_TYPE="docker-desktop"
    echo "✅ Detected Docker Desktop cluster"
else
    echo "⚠️  Unknown cluster type, assuming images are available"
    exit 0
fi

# List of images to load
IMAGES=(
    "aitourist/gateway:latest"
    "aitourist/ml-service:latest"
    "aitourist/frontend:latest"
)

case $CLUSTER_TYPE in
    minikube)
        echo ""
        echo "Loading images into Minikube..."
        for image in "${IMAGES[@]}"; do
            echo "  → $image"
            minikube image load "$image"
        done
        ;;
        
    kind)
        echo ""
        echo "Loading images into Kind cluster '$CLUSTER_NAME'..."
        for image in "${IMAGES[@]}"; do
            echo "  → $image"
            kind load docker-image "$image" --name "$CLUSTER_NAME"
        done
        ;;
        
    docker-desktop)
        echo ""
        echo "Docker Desktop cluster detected - images should be available automatically"
        echo "If you still see ErrImageNeverPull, try restarting Docker Desktop"
        ;;
esac

echo ""
echo "✅ Images loaded successfully!"
echo ""
echo "💡 Restart deployments:"
echo "   kubectl rollout restart deployment -n aitourist"