#!/bin/bash
set -e

ENV_FILE=".env"
OUTPUT_FILE=".env.yaml"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env file not found!"
  exit 1
fi

echo "📝 Converting .env to .env.yaml..."

source $ENV_FILE

cat > $OUTPUT_FILE << EOF
# Generated from .env file
# This file overrides helm/ai-tourist/values.yaml

global:
  environment: production
  
secrets:
  dbPassword: "${DB_PASSWORD:-change_in_production}"
  openaiApiKey: "${OPENAI_API_KEY:-}"
  anthropicApiKey: "${ANTHROPIC_API_KEY:-}"
  twogisApiKey: "${TWOGIS_API_KEY:-}"
  jwtSecret: "${JWT_SECRET_KEY:-generate_random_secret}"
  encryptionKey: "${ENCRYPTION_KEY:-generate_random_key}"

llm:
  provider: "${LLM_PROVIDER:-openai}"
  model: "${LLM_MODEL:-gpt-4o-mini}"

scaling:
  gateway:
    replicas: ${GATEWAY_REPLICAS:-2}
  embedding:
    replicas: 2
  ranking:
    replicas: 2
  routePlanner:
    replicas: 2
  llm:
    replicas: 1
  geocoding:
    replicas: 1
  poi:
    replicas: 1

resources:
  gateway:
    memory: "${GATEWAY_MEMORY:-512Mi}"
    cpu: "500m"
  embedding:
    memory: "${ML_MEMORY:-2Gi}"
    cpu: "1000m"
  ranking:
    memory: "${ML_MEMORY:-2Gi}"
    cpu: "1000m"
  routePlanner:
    memory: "1Gi"
    cpu: "500m"
  llm:
    memory: "512Mi"
    cpu: "250m"
  geocoding:
    memory: "256Mi"
    cpu: "250m"
  poi:
    memory: "1Gi"
    cpu: "500m"
  postgresql:
    memory: "${POSTGRES_MEMORY:-2Gi}"
    cpu: "1000m"
  redis:
    memory: "${REDIS_MEMORY:-512Mi}"
    cpu: "250m"

monitoring:
  enabled: true
  grafana:
    password: "${GRAFANA_PASSWORD:-admin}"
EOF

echo "✅ Generated $OUTPUT_FILE"