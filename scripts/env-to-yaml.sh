#!/bin/bash
set -e

ENV_FILE=".env"
OUTPUT_FILE="values.yaml"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env file not found!"
  exit 1
fi

echo "📝 Converting .env to values.yaml..."

# Load environment variables
source $ENV_FILE

cat > $OUTPUT_FILE << EOF
# Generated from .env file
# This file overrides helm/ai-tourist/values.yaml

# Global settings
global:
  environment: ${ENVIRONMENT:-production}

# Secrets (override with .env.yaml)
secrets:
  dbPassword: "${DB_PASSWORD:-change_in_production}"
  openaiApiKey: "${OPENAI_API_KEY:-}"
  anthropicApiKey: "${ANTHROPIC_API_KEY:-}"
  twogisApiKey: "${TWOGIS_API_KEY:-}"
  jwtSecret: "${JWT_SECRET_KEY:-generate_random_secret}"
  encryptionKey: "${ENCRYPTION_KEY:-generate_random_key}"

# LLM Configuration
llm:
  provider: "${LLM_PROVIDER:-openai}"
  model: "${LLM_MODEL:-gpt-4o-mini}"

# Frontend
frontend:
  replicas: ${FRONTEND_REPLICAS:-2}
  image:
    tag: "${FRONTEND_IMAGE_TAG:-latest}"
  resources:
    requests:
      memory: "${FRONTEND_MEMORY_REQUEST:-128Mi}"
      cpu: "${FRONTEND_CPU_REQUEST:-100m}"
    limits:
      memory: "${FRONTEND_MEMORY_LIMIT:-256Mi}"
      cpu: "${FRONTEND_CPU_LIMIT:-200m}"

# API Gateway
apiGateway:
  replicas: ${API_GATEWAY_REPLICAS:-2}
  image:
    tag: "${API_GATEWAY_IMAGE_TAG:-latest}"
  resources:
    requests:
      memory: "${API_GATEWAY_MEMORY_REQUEST:-256Mi}"
      cpu: "${API_GATEWAY_CPU_REQUEST:-200m}"
    limits:
      memory: "${API_GATEWAY_MEMORY_LIMIT:-512Mi}"
      cpu: "${API_GATEWAY_CPU_LIMIT:-500m}"

# Embedding Service
embeddingService:
  replicas: ${EMBEDDING_REPLICAS:-2}
  image:
    tag: "${EMBEDDING_IMAGE_TAG:-latest}"
  batchSize: ${EMBEDDING_BATCH_SIZE:-32}
  model: "${EMBEDDING_MODEL:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}"
  resources:
    requests:
      memory: "${EMBEDDING_MEMORY_REQUEST:-512Mi}"
      cpu: "${EMBEDDING_CPU_REQUEST:-500m}"
    limits:
      memory: "${EMBEDDING_MEMORY_LIMIT:-1Gi}"
      cpu: "${EMBEDDING_CPU_LIMIT:-1000m}"

# Ranking Service
rankingService:
  replicas: ${RANKING_REPLICAS:-2}
  image:
    tag: "${RANKING_IMAGE_TAG:-latest}"
  resources:
    requests:
      memory: "${RANKING_MEMORY_REQUEST:-256Mi}"
      cpu: "${RANKING_CPU_REQUEST:-200m}"
    limits:
      memory: "${RANKING_MEMORY_LIMIT:-512Mi}"
      cpu: "${RANKING_CPU_LIMIT:-500m}"

# Route Planner Service
routePlannerService:
  replicas: ${ROUTE_PLANNER_REPLICAS:-2}
  image:
    tag: "${ROUTE_PLANNER_IMAGE_TAG:-latest}"
  resources:
    requests:
      memory: "${ROUTE_PLANNER_MEMORY_REQUEST:-256Mi}"
      cpu: "${ROUTE_PLANNER_CPU_REQUEST:-200m}"
    limits:
      memory: "${ROUTE_PLANNER_MEMORY_LIMIT:-512Mi}"
      cpu: "${ROUTE_PLANNER_CPU_LIMIT:-500m}"

# LLM Service
llmService:
  replicas: ${LLM_SERVICE_REPLICAS:-1}
  image:
    tag: "${LLM_SERVICE_IMAGE_TAG:-latest}"
  resources:
    requests:
      memory: "${LLM_SERVICE_MEMORY_REQUEST:-256Mi}"
      cpu: "${LLM_SERVICE_CPU_REQUEST:-200m}"
    limits:
      memory: "${LLM_SERVICE_MEMORY_LIMIT:-512Mi}"
      cpu: "${LLM_SERVICE_CPU_LIMIT:-500m}"

# Geocoding Service
geocodingService:
  replicas: ${GEOCODING_REPLICAS:-1}
  image:
    tag: "${GEOCODING_IMAGE_TAG:-latest}"
  resources:
    requests:
      memory: "${GEOCODING_MEMORY_REQUEST:-128Mi}"
      cpu: "${GEOCODING_CPU_REQUEST:-100m}"
    limits:
      memory: "${GEOCODING_MEMORY_LIMIT:-256Mi}"
      cpu: "${GEOCODING_CPU_LIMIT:-200m}"

# POI Service
poiService:
  replicas: ${POI_REPLICAS:-1}
  image:
    tag: "${POI_IMAGE_TAG:-latest}"
  resources:
    requests:
      memory: "${POI_MEMORY_REQUEST:-256Mi}"
      cpu: "${POI_CPU_REQUEST:-200m}"
    limits:
      memory: "${POI_MEMORY_LIMIT:-512Mi}"
      cpu: "${POI_CPU_LIMIT:-500m}"

# PostgreSQL
postgresql:
  enabled: ${POSTGRESQL_ENABLED:-true}
  image:
    tag: "${POSTGRESQL_IMAGE_TAG:-16-alpine}"
  persistence:
    enabled: ${POSTGRESQL_PERSISTENCE_ENABLED:-true}
    size: ${POSTGRESQL_STORAGE_SIZE:-1Gi}
  resources:
    requests:
      memory: "${POSTGRESQL_MEMORY_REQUEST:-256Mi}"
      cpu: "${POSTGRESQL_CPU_REQUEST:-250m}"
    limits:
      memory: "${POSTGRESQL_MEMORY_LIMIT:-512Mi}"
      cpu: "${POSTGRESQL_CPU_LIMIT:-500m}"

# Redis
redis:
  enabled: ${REDIS_ENABLED:-true}
  image:
    tag: "${REDIS_IMAGE_TAG:-7-alpine}"
  persistence:
    enabled: ${REDIS_PERSISTENCE_ENABLED:-true}
    size: ${REDIS_STORAGE_SIZE:-1Gi}
  resources:
    requests:
      memory: "${REDIS_MEMORY_REQUEST:-128Mi}"
      cpu: "${REDIS_CPU_REQUEST:-100m}"
    limits:
      memory: "${REDIS_MEMORY_LIMIT:-256Mi}"
      cpu: "${REDIS_CPU_LIMIT:-200m}"

# Ingress
ingress:
  enabled: ${INGRESS_ENABLED:-true}
  className: ${INGRESS_CLASS:-nginx}
EOF

echo "✅ Generated $OUTPUT_FILE"
echo ""
echo "📋 This file can be used to override helm/ai-tourist/values.yaml:"
echo "   - All services with correct names (apiGateway, embeddingService, etc.)"
echo "   - Resources nested within each service"
echo "   - Image tags configurable per service"
echo "   - Database and Redis settings"
echo ""
echo "💡 Usage:"
echo "   helm upgrade --install ai-tourist ./helm/ai-tourist -f $OUTPUT_FILE"