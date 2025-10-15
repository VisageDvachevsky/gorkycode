#!/bin/bash
set -e

echo "🔍 AI-Tourist Setup Check"
echo "================================"
echo ""

HAS_ERRORS=0

echo "📦 Checking dependencies..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    HAS_ERRORS=1
else
    echo "✅ Docker: $(docker --version | cut -d' ' -f3)"
fi

if ! command -v minikube &> /dev/null; then
    echo "⚠️  Minikube not found (will be installed by 'make k8s-install')"
else
    echo "✅ Minikube: $(minikube version --short)"
fi

if ! command -v kubectl &> /dev/null; then
    echo "⚠️  kubectl not found (will be installed by 'make k8s-install')"
else
    echo "✅ kubectl: $(kubectl version --client --short 2>/dev/null || echo 'installed')"
fi

if ! command -v helm &> /dev/null; then
    echo "⚠️  Helm not found (will be installed by 'make k8s-install')"
else
    echo "✅ Helm: $(helm version --short)"
fi

echo ""
echo "📄 Checking files..."

if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    echo "   Run: cp .env.example .env"
    HAS_ERRORS=1
else
    echo "✅ .env file exists"
    
    source .env
    
    if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
        echo "⚠️  Warning: No LLM API key configured"
        echo "   Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"
    else
        echo "✅ LLM API key configured"
    fi
    
    if [ -z "$TWOGIS_API_KEY" ]; then
        echo "⚠️  Warning: TWOGIS_API_KEY not configured"
        echo "   Get your key at https://dev.2gis.com"
    else
        echo "✅ 2GIS API key configured"
    fi
fi

if [ ! -d "proto" ]; then
    echo "❌ proto/ directory not found"
    HAS_ERRORS=1
else
    echo "✅ proto/ directory exists"
fi

if [ ! -d "services" ]; then
    echo "❌ services/ directory not found"
    HAS_ERRORS=1
else
    echo "✅ services/ directory exists"
fi

if [ ! -d "helm/ai-tourist" ]; then
    echo "❌ helm/ai-tourist/ directory not found"
    HAS_ERRORS=1
else
    echo "✅ Helm chart exists"
fi

echo ""
echo "💾 Checking disk space..."

AVAILABLE_GB=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')

if [ "$AVAILABLE_GB" -lt 20 ]; then
    echo "⚠️  Warning: Low disk space (${AVAILABLE_GB}GB available)"
    echo "   Recommended: 20GB+ for Kubernetes cluster"
else
    echo "✅ Disk space: ${AVAILABLE_GB}GB available"
fi

echo ""
echo "================================"

if [ $HAS_ERRORS -eq 1 ]; then
    echo "❌ Setup check failed!"
    echo ""
    echo "Please fix the errors above before running 'make k8s-deploy'"
    exit 1
else
    echo "✅ Setup check passed!"
    echo ""
    echo "You're ready to deploy!"
    echo ""
    echo "Next steps:"
    echo "  1. make k8s-install    # Install Kubernetes (if not done)"
    echo "  2. make k8s-deploy     # Deploy the application"
    echo ""
fi