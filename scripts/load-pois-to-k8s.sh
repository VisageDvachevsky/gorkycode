#!/bin/bash
set -e

NAMESPACE="ai-tourist"
POI_FILE="data/poi.json"

echo "📦 Loading POIs from $POI_FILE to Kubernetes..."

if [ ! -f "$POI_FILE" ]; then
    echo "❌ File $POI_FILE not found!"
    exit 1
fi

POI_COUNT=$(jq length "$POI_FILE" 2>/dev/null || echo "unknown")
echo "📊 Found $POI_COUNT POIs in file"

echo "🔑 Getting database password..."
DB_PASSWORD=$(kubectl get secret ai-tourist-secrets -n $NAMESPACE -o jsonpath='{.data.DB_PASSWORD}' | base64 -d)

echo "🔌 Starting port-forward to PostgreSQL..."
kubectl port-forward -n $NAMESPACE svc/ai-tourist-postgresql 5432:5432 > /dev/null 2>&1 &
PF_PID=$!

sleep 3

if ! python3 -c "import asyncpg" 2>/dev/null; then
    echo "📦 Installing asyncpg..."
    pip install asyncpg > /dev/null 2>&1
fi

echo "⚡ Loading POIs..."
export DB_PASSWORD="$DB_PASSWORD"
export POI_JSON_PATH="$POI_FILE"
python3 scripts/load_pois.py

kill $PF_PID 2>/dev/null || true

echo ""
echo "✅ POI loading complete!"