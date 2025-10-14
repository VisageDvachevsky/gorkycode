#!/bin/bash
set -e

echo "🔧 Quick Fix for your project structure"
echo "========================================"
echo ""

# Detect structure
HAS_SERVICES_GATEWAY=false
HAS_BACKEND=false
HAS_SERVICES_ML=false

if [ -d "services/gateway" ]; then
    HAS_SERVICES_GATEWAY=true
fi

if [ -d "backend" ]; then
    HAS_BACKEND=true
fi

if [ -d "services/ml" ]; then
    HAS_SERVICES_ML=true
fi

echo "📊 Detected structure:"
echo "   services/gateway: $HAS_SERVICES_GATEWAY"
echo "   backend: $HAS_BACKEND"
echo "   services/ml: $HAS_SERVICES_ML"
echo ""

# Decision for Gateway
if [ "$HAS_SERVICES_GATEWAY" = true ] && [ "$HAS_BACKEND" = true ]; then
    echo "❓ You have both services/gateway/ and backend/"
    echo ""
    echo "Which one should be used as the main API Gateway for k8s?"
    echo "   1) services/gateway/ (recommended for microservices)"
    echo "   2) backend/ (if it's your main API)"
    echo ""
    read -p "Enter choice [1-2]: " gateway_choice
    
    if [ "$gateway_choice" = "1" ]; then
        GATEWAY_PATH="services/gateway"
    else
        GATEWAY_PATH="backend"
    fi
elif [ "$HAS_SERVICES_GATEWAY" = true ]; then
    GATEWAY_PATH="services/gateway"
elif [ "$HAS_BACKEND" = true ]; then
    GATEWAY_PATH="backend"
fi

echo ""
echo "✅ Will use: $GATEWAY_PATH as Gateway"

# ML Service
if [ "$HAS_SERVICES_ML" = true ]; then
    ML_PATH="services/ml"
    echo "✅ Will use: services/ml/ as ML Service"
else
    echo "⚠️  No ML service found - will skip in k8s deployment"
    ML_PATH=""
fi

# Frontend
if [ -d "frontend" ]; then
    FRONTEND_PATH="frontend"
    echo "✅ Will use: frontend/"
else
    echo "❌ Frontend not found"
    exit 1
fi

echo ""
echo "💾 Saving configuration..."

# Create config file for build script
cat > .k8s-config << EOF
GATEWAY_PATH=$GATEWAY_PATH
ML_PATH=$ML_PATH
FRONTEND_PATH=$FRONTEND_PATH
EOF

echo "✅ Configuration saved to .k8s-config"
echo ""
echo "🚀 Now you can run:"
echo "   make k8s-build"
echo "   make k8s-apply"