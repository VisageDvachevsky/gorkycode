#!/bin/bash
set -e

echo "🗄️  Running database migrations..."

NAMESPACE="aitourist"
POD=$(kubectl get pod -n $NAMESPACE -l app=postgres -o jsonpath="{.items[0].metadata.name}")

if [ -z "$POD" ]; then
    echo "❌ PostgreSQL pod not found"
    exit 1
fi

echo "📍 Found PostgreSQL pod: $POD"

if [ ! -f gateway/db/init.sql ]; then
    echo "❌ Migration file not found: gateway/db/init.sql"
    exit 1
fi

echo "📤 Copying migration file..."
kubectl cp gateway/db/init.sql $NAMESPACE/$POD:/tmp/init.sql

echo "🔄 Executing migrations..."
kubectl exec -n $NAMESPACE $POD -- psql -U postgres -d aitourist -f /tmp/init.sql

echo "✅ Migrations completed successfully!"

echo ""
echo "📊 Database tables:"
kubectl exec -n $NAMESPACE $POD -- psql -U postgres -d aitourist -c "\dt"