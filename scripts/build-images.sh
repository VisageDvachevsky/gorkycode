#!/bin/bash
set -e

echo "🐳 Building Docker images for Kubernetes..."

# Try to load saved config
if [ -f ".k8s-config" ]; then
    echo "📝 Loading saved configuration..."
    source .k8s-config
    GATEWAY_DIR="$GATEWAY_PATH"
    ML_DIR="$ML_PATH"
    FRONTEND_DIR="$FRONTEND_PATH"
else
    # Auto-detect project structure
    GATEWAY_DIR=""
    ML_DIR=""
    FRONTEND_DIR=""

    # Gateway detection (prefer services/gateway over backend)
    if [ -d "services/gateway" ]; then
        GATEWAY_DIR="services/gateway"
    elif [ -d "gateway" ]; then
        GATEWAY_DIR="gateway"
    elif [ -d "backend" ]; then
        GATEWAY_DIR="backend"
    elif [ -d "api" ]; then
        GATEWAY_DIR="api"
    fi

    # ML Service detection
    if [ -d "services/ml" ]; then
        ML_DIR="services/ml"
    elif [ -d "ml-service" ]; then
        ML_DIR="ml-service"
    elif [ -d "ml_service" ]; then
        ML_DIR="ml_service"
    elif [ -d "ml" ]; then
        ML_DIR="ml"
    fi

    # Frontend detection
    if [ -d "frontend" ]; then
        FRONTEND_DIR="frontend"
    elif [ -d "client" ]; then
        FRONTEND_DIR="client"
    elif [ -d "web" ]; then
        FRONTEND_DIR="web"
    fi
fi

# Build Gateway
if [ -n "$GATEWAY_DIR" ]; then
    echo ""
    echo "📦 Building Gateway from $GATEWAY_DIR/..."
    if [ -f "$GATEWAY_DIR/Dockerfile" ]; then
        docker build -t aitourist/gateway:latest -f "$GATEWAY_DIR/Dockerfile" "$GATEWAY_DIR/"
        echo "✅ Gateway image built"
    else
        echo "❌ Dockerfile not found in $GATEWAY_DIR/"
        exit 1
    fi
else
    echo "❌ Gateway directory not found"
    echo "💡 Run: bash scripts/quickfix.sh to configure"
    exit 1
fi

# Build ML Service
if [ -n "$ML_DIR" ]; then
    echo ""
    echo "🧠 Building ML Service from $ML_DIR/..."
    if [ -f "$ML_DIR/Dockerfile" ]; then
        docker build -t aitourist/ml-service:latest -f "$ML_DIR/Dockerfile" "$ML_DIR/"
        echo "✅ ML Service image built"
    else
        echo "❌ Dockerfile not found in $ML_DIR/"
        exit 1
    fi
else
    echo "⚠️  ML Service directory not found, skipping..."
    echo "💡 If you need ML service, run: bash scripts/quickfix.sh"
fi

# Build Frontend
if [ -n "$FRONTEND_DIR" ]; then
    echo ""
    echo "🎨 Building Frontend from $FRONTEND_DIR/..."
    if [ -f "$FRONTEND_DIR/Dockerfile" ]; then
        docker build -t aitourist/frontend:latest -f "$FRONTEND_DIR/Dockerfile" "$FRONTEND_DIR/"
        echo "✅ Frontend image built"
    else
        echo "❌ Dockerfile not found in $FRONTEND_DIR/"
        exit 1
    fi
else
    echo "❌ Frontend directory not found"
    echo "💡 Run: bash scripts/quickfix.sh to configure"
    exit 1
fi

echo ""
echo "✅ Image build complete!"
echo ""
echo "📋 Built images:"
docker images | grep aitourist || echo "No aitourist images found"

echo ""
echo "💡 Used structure:"
echo "   Gateway: ${GATEWAY_DIR}"
echo "   ML Service: ${ML_DIR:-not configured}"
echo "   Frontend: ${FRONTEND_DIR}"

echo ""
echo "💡 Next steps:"
echo "   1. Apply k8s manifests: make k8s-apply"
echo "   2. Check status: make k8s-status"
echo "   3. View logs: make k8s-logs"