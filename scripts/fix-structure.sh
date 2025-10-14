#!/bin/bash
set -e

echo "🔧 Fixing project structure for Kubernetes deployment..."
echo ""

# Create k8s directory if missing
if [ ! -d "k8s" ]; then
    echo "📁 Creating k8s/ directory..."
    mkdir -p k8s
fi

# Create scripts directory if missing
if [ ! -d "scripts" ]; then
    echo "📁 Creating scripts/ directory..."
    mkdir -p scripts
fi

# Check and suggest fixes for backend
if [ ! -d "gateway" ]; then
    if [ -d "backend" ]; then
        echo "📦 Found backend/ - will use as gateway in Docker builds"
    elif [ -d "api" ]; then
        echo "📦 Found api/ - will use as gateway in Docker builds"
    else
        echo "❌ No backend directory found!"
        echo ""
        echo "💡 Please create one of:"
        echo "   - gateway/  (recommended)"
        echo "   - backend/"
        echo "   - api/"
        echo ""
        echo "With structure:"
        echo "   gateway/"
        echo "   ├── app/"
        echo "   │   ├── main.py"
        echo "   │   └── ..."
        echo "   ├── pyproject.toml"
        echo "   └── Dockerfile"
    fi
fi

# Check ML service
if [ ! -d "ml-service" ] && [ ! -d "ml_service" ] && [ ! -d "ml" ]; then
    echo "⚠️  No ML service directory found!"
    echo ""
    echo "💡 Options:"
    echo "   1. Create ml-service/ directory"
    echo "   2. Use existing docker-compose service name"
    echo ""
    read -p "Create ml-service/ directory? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p ml-service/app
        echo "✅ Created ml-service/ directory"
        echo "   Please add your ML service code there"
    fi
fi

# Check frontend
if [ ! -d "frontend" ]; then
    if [ -d "client" ]; then
        echo "🎨 Found client/ - will use as frontend in Docker builds"
    elif [ -d "web" ]; then
        echo "🎨 Found web/ - will use as frontend in Docker builds"
    else
        echo "⚠️  No frontend directory found!"
        echo ""
        echo "💡 Options:"
        echo "   1. Create frontend/ directory"
        echo "   2. Use existing React app directory"
        echo ""
        read -p "Create frontend/ directory? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mkdir -p frontend/src
            echo "✅ Created frontend/ directory"
            echo "   Please add your React app there"
        fi
    fi
fi

# Check Dockerfiles
echo ""
echo "🐳 Checking Dockerfiles..."

for dir in gateway backend api ml-service ml_service ml frontend client web; do
    if [ -d "$dir" ] && [ ! -f "$dir/Dockerfile" ]; then
        echo "⚠️  $dir/ exists but no Dockerfile found"
        
        if [[ "$dir" == gateway* ]] || [[ "$dir" == backend* ]] || [[ "$dir" == api* ]]; then
            echo "   Creating default FastAPI Dockerfile..."
            cat > "$dir/Dockerfile" << 'EOF'
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base AS builder
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --only main --no-root --no-directory

FROM base AS runtime
COPY --from=builder /app/.venv /app/.venv
COPY . .

ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONPATH=/app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
            echo "   ✅ Created Dockerfile"
        fi
    fi
done

echo ""
echo "✅ Structure check complete!"
echo ""
echo "📋 Summary:"
bash scripts/check-structure.sh 2>/dev/null || true

echo ""
echo "💡 Next steps:"
echo "   1. Review generated Dockerfiles if any"
echo "   2. Run: make k8s-build"
echo "   3. Run: make k8s-apply"