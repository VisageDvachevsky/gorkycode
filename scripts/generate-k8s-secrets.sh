#!/bin/bash
set -e

ENV_FILE="${1:-.env}"
TEMPLATE_FILE="k8s/02-secrets.yaml.template"
OUTPUT_FILE="k8s/02-secrets.yaml"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found"
    exit 1
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "❌ Error: $TEMPLATE_FILE not found"
    exit 1
fi

echo "🔐 Generating k8s secrets from $ENV_FILE..."

# Convert Windows line endings to Unix if needed
dos2unix "$ENV_FILE" 2>/dev/null || sed -i 's/\r$//' "$ENV_FILE" 2>/dev/null || true

# Load environment variables, stripping carriage returns
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue
    
    # Strip whitespace and carriage returns
    key=$(echo "$key" | tr -d '\r' | xargs)
    value=$(echo "$value" | tr -d '\r' | xargs)
    
    # Export the variable
    export "$key=$value"
done < "$ENV_FILE"

# Generate missing secrets
if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "generate_random_secret_for_jwt" ]; then
    echo "🔑 Generating JWT_SECRET_KEY..."
    export JWT_SECRET_KEY=$(openssl rand -hex 32)
fi

if [ -z "$ENCRYPTION_KEY" ] || [ "$ENCRYPTION_KEY" = "generate_random_32_byte_key" ]; then
    echo "🔑 Generating ENCRYPTION_KEY..."
    export ENCRYPTION_KEY=$(openssl rand -base64 32)
fi

if [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" = "change_in_production" ]; then
    echo "🔑 Generating DB_PASSWORD..."
    export DB_PASSWORD=$(openssl rand -base64 16)
fi

if [ -z "$GRAFANA_PASSWORD" ] || [ "$GRAFANA_PASSWORD" = "admin" ]; then
    echo "🔑 Generating GRAFANA_PASSWORD..."
    export GRAFANA_PASSWORD=$(openssl rand -base64 16)
fi

# Substitute environment variables in template
envsubst < "$TEMPLATE_FILE" > "$OUTPUT_FILE"

echo "✅ Secrets generated at $OUTPUT_FILE"
echo ""
echo "📝 Generated credentials:"
echo "   JWT_SECRET_KEY: ${JWT_SECRET_KEY:0:10}..."
echo "   ENCRYPTION_KEY: ${ENCRYPTION_KEY:0:10}..."
echo "   DB_PASSWORD: ${DB_PASSWORD:0:8}..."
echo "   GRAFANA_PASSWORD: ${GRAFANA_PASSWORD:0:8}..."
echo ""
echo "⚠️  Keep these credentials secure!"