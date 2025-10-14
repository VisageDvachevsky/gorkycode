#!/bin/bash

echo "📂 Analyzing project structure..."
echo ""

# Gateway detection
if [ -d "services/gateway" ]; then
    echo "✅ services/gateway/ found (will use as gateway)"
elif [ -d "gateway" ]; then
    echo "✅ gateway/ found"
elif [ -d "backend" ]; then
    echo "✅ backend/ found (will use as gateway)"
elif [ -d "api" ]; then
    echo "✅ api/ found (will use as gateway)"
else
    echo "❌ Gateway/backend directory not found"
fi

# ML Service detection
if [ -d "services/ml" ]; then
    echo "✅ services/ml/ found (will use as ML service)"
elif [ -d "ml-service" ]; then
    echo "✅ ml-service/ found"
elif [ -d "ml_service" ]; then
    echo "✅ ml_service/ found (will rename to ml-service)"
elif [ -d "ml" ]; then
    echo "✅ ml/ found (will use as ML service)"
else
    echo "❌ ML service directory not found"
fi

# Frontend detection
if [ -d "frontend" ]; then
    echo "✅ frontend/ found"
elif [ -d "client" ]; then
    echo "✅ client/ found (will use as frontend)"
elif [ -d "web" ]; then
    echo "✅ web/ found (will use as frontend)"
else
    echo "❌ Frontend directory not found"
fi

echo ""
echo "📋 Current directory structure:"
ls -la

echo ""
echo "🔍 Docker-related files:"
find . -maxdepth 4 -name "Dockerfile" -o -name "docker-compose*.yml" | grep -v node_modules | head -20

echo ""
echo "🐍 Python projects:"
find . -maxdepth 3 -name "pyproject.toml" -o -name "requirements.txt" | grep -v node_modules | head -10

echo ""
echo "📦 Node.js projects:"
find . -maxdepth 3 -name "package.json" | grep -v node_modules | head -5

echo ""
echo "🎯 For k8s deployment we will use:"
if [ -d "services/gateway" ]; then
    echo "   Gateway: services/gateway/"
elif [ -d "backend" ]; then
    echo "   Gateway: backend/"
fi

if [ -d "services/ml" ]; then
    echo "   ML Service: services/ml/"
fi

if [ -d "frontend" ]; then
    echo "   Frontend: frontend/"
fi