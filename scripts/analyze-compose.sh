#!/bin/bash

echo "🔍 Analyzing docker-compose configuration..."
echo ""

if [ -f "docker-compose.yml" ]; then
    echo "📋 Services defined in docker-compose.yml:"
    grep -E "^  [a-z-]+:" docker-compose.yml | sed 's/://g' | sed 's/^  /  - /'
    
    echo ""
    echo "🔌 Port mappings:"
    grep -E "ports:|[0-9]+:[0-9]+" docker-compose.yml | head -20
    
    echo ""
    echo "🐳 Build contexts:"
    grep -E "build:|context:" docker-compose.yml | head -20
fi

echo ""
echo "💡 Recommendation for k8s deployment:"
echo ""

# Check services directory
if [ -d "services/gateway" ] && [ -f "services/gateway/Dockerfile" ]; then
    echo "✅ Use services/gateway/ as main API Gateway"
fi

if [ -d "services/ml" ] && [ -f "services/ml/Dockerfile" ]; then
    echo "✅ Use services/ml/ as ML Service"
fi

if [ -d "backend" ] && [ -f "backend/Dockerfile" ]; then
    echo "⚠️  backend/ also has Dockerfile"
    echo "   Check if it's needed separately or if services/gateway replaces it"
fi

if [ -d "frontend" ] && [ -f "frontend/Dockerfile" ]; then
    echo "✅ Use frontend/ for React app"
fi

echo ""
echo "🎯 For microservices architecture:"
echo "   Prefer services/* directories over monolithic backend"