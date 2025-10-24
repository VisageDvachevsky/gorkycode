#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"
OUTPUT_FILE="${2:-.env.yaml}"
HELM_SECRETS_FILE="helm/ai-tourist/secrets.yaml"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "❌ .env file not found at ${ENV_FILE}!"
  exit 1
fi

if [[ ! -d "$(dirname "${HELM_SECRETS_FILE}")" ]]; then
  echo "❌ Helm chart directory not found at $(dirname "${HELM_SECRETS_FILE}")"
  exit 1
fi

source_env() {
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
}

source_env

required_vars=(DB_PASSWORD TWOGIS_API_KEY JWT_SECRET_KEY ENCRYPTION_KEY)
missing=()
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    missing+=("${var}")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "❌ Missing required variables: ${missing[*]}"
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "⚠️  No LLM API keys provided. The LLM service will use fallback responses."
fi

validate_positive_integer() {
  local name="$1"
  local value="$2"
  if [[ -n "${value}" && ! "${value}" =~ ^[0-9]+$ ]]; then
    echo "❌ ${name} must be a positive integer (got '${value}')"
    exit 1
  fi
}

normalize_bool() {
  local name="$1"
  local value="${2:-false}"
  local lower
  lower="$(echo "${value}" | tr '[:upper:]' '[:lower:]')"
  case "${lower}" in
    true|false)
      printf "%s" "${lower}"
      ;;
    *)
      echo "❌ ${name} must be true or false (got '${value}')"
      exit 1
      ;;
  esac
}

yaml_escape() {
  local value="${1:-}"
  value="${value//\\/\\\\}"
  value="${value//"/\\"}"
  printf '%s' "${value}"
}

validate_positive_integer "FRONTEND_REPLICAS" "${FRONTEND_REPLICAS:-2}"
validate_positive_integer "API_GATEWAY_REPLICAS" "${API_GATEWAY_REPLICAS:-2}"
validate_positive_integer "EMBEDDING_REPLICAS" "${EMBEDDING_REPLICAS:-2}"
validate_positive_integer "EMBEDDING_BATCH_SIZE" "${EMBEDDING_BATCH_SIZE:-32}"
validate_positive_integer "RANKING_REPLICAS" "${RANKING_REPLICAS:-2}"
validate_positive_integer "ROUTE_PLANNER_REPLICAS" "${ROUTE_PLANNER_REPLICAS:-2}"
validate_positive_integer "LLM_SERVICE_REPLICAS" "${LLM_SERVICE_REPLICAS:-1}"
validate_positive_integer "GEOCODING_REPLICAS" "${GEOCODING_REPLICAS:-1}"
validate_positive_integer "POI_REPLICAS" "${POI_REPLICAS:-1}"

POSTGRESQL_ENABLED_VALUE="$(normalize_bool "POSTGRESQL_ENABLED" "${POSTGRESQL_ENABLED:-true}")"
POSTGRESQL_PERSISTENCE_ENABLED_VALUE="$(normalize_bool "POSTGRESQL_PERSISTENCE_ENABLED" "${POSTGRESQL_PERSISTENCE_ENABLED:-true}")"
REDIS_ENABLED_VALUE="$(normalize_bool "REDIS_ENABLED" "${REDIS_ENABLED:-true}")"
REDIS_PERSISTENCE_ENABLED_VALUE="$(normalize_bool "REDIS_PERSISTENCE_ENABLED" "${REDIS_PERSISTENCE_ENABLED:-true}")"
INGRESS_ENABLED_VALUE="$(normalize_bool "INGRESS_ENABLED" "${INGRESS_ENABLED:-true}")"

cat > "${OUTPUT_FILE}" <<EOF_YAML
secrets:
  dbPassword: "$(yaml_escape "${DB_PASSWORD}")"
  openaiApiKey: "$(yaml_escape "${OPENAI_API_KEY:-}")"
  anthropicApiKey: "$(yaml_escape "${ANTHROPIC_API_KEY:-}")"
  twogisApiKey: "$(yaml_escape "${TWOGIS_API_KEY}")"
  jwtSecret: "$(yaml_escape "${JWT_SECRET_KEY}")"
  encryptionKey: "$(yaml_escape "${ENCRYPTION_KEY}")"

frontend:
  replicas: ${FRONTEND_REPLICAS:-2}
  image:
    tag: "$(yaml_escape "${FRONTEND_IMAGE_TAG:-latest}")"
  resources:
    requests:
      memory: "$(yaml_escape "${FRONTEND_MEMORY_REQUEST:-128Mi}")"
      cpu: "$(yaml_escape "${FRONTEND_CPU_REQUEST:-100m}")"
    limits:
      memory: "$(yaml_escape "${FRONTEND_MEMORY_LIMIT:-256Mi}")"
      cpu: "$(yaml_escape "${FRONTEND_CPU_LIMIT:-200m}")"

apiGateway:
  replicas: ${API_GATEWAY_REPLICAS:-2}
  image:
    tag: "$(yaml_escape "${API_GATEWAY_IMAGE_TAG:-latest}")"
  resources:
    requests:
      memory: "$(yaml_escape "${API_GATEWAY_MEMORY_REQUEST:-256Mi}")"
      cpu: "$(yaml_escape "${API_GATEWAY_CPU_REQUEST:-200m}")"
    limits:
      memory: "$(yaml_escape "${API_GATEWAY_MEMORY_LIMIT:-512Mi}")"
      cpu: "$(yaml_escape "${API_GATEWAY_CPU_LIMIT:-500m}")"

embeddingService:
  replicas: ${EMBEDDING_REPLICAS:-2}
  image:
    tag: "$(yaml_escape "${EMBEDDING_IMAGE_TAG:-latest}")"
  batchSize: ${EMBEDDING_BATCH_SIZE:-32}
  model: "$(yaml_escape "${EMBEDDING_MODEL:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}")"
  resources:
    requests:
      memory: "$(yaml_escape "${EMBEDDING_MEMORY_REQUEST:-512Mi}")"
      cpu: "$(yaml_escape "${EMBEDDING_CPU_REQUEST:-500m}")"
    limits:
      memory: "$(yaml_escape "${EMBEDDING_MEMORY_LIMIT:-1Gi}")"
      cpu: "$(yaml_escape "${EMBEDDING_CPU_LIMIT:-1000m}")"

rankingService:
  replicas: ${RANKING_REPLICAS:-2}
  image:
    tag: "$(yaml_escape "${RANKING_IMAGE_TAG:-latest}")"
  resources:
    requests:
      memory: "$(yaml_escape "${RANKING_MEMORY_REQUEST:-256Mi}")"
      cpu: "$(yaml_escape "${RANKING_CPU_REQUEST:-200m}")"
    limits:
      memory: "$(yaml_escape "${RANKING_MEMORY_LIMIT:-512Mi}")"
      cpu: "$(yaml_escape "${RANKING_CPU_LIMIT:-500m}")"

routePlannerService:
  replicas: ${ROUTE_PLANNER_REPLICAS:-2}
  image:
    tag: "$(yaml_escape "${ROUTE_PLANNER_IMAGE_TAG:-latest}")"
  resources:
    requests:
      memory: "$(yaml_escape "${ROUTE_PLANNER_MEMORY_REQUEST:-256Mi}")"
      cpu: "$(yaml_escape "${ROUTE_PLANNER_CPU_REQUEST:-200m}")"
    limits:
      memory: "$(yaml_escape "${ROUTE_PLANNER_MEMORY_LIMIT:-512Mi}")"
      cpu: "$(yaml_escape "${ROUTE_PLANNER_CPU_LIMIT:-500m}")"

llmService:
  replicas: ${LLM_SERVICE_REPLICAS:-1}
  image:
    tag: "$(yaml_escape "${LLM_SERVICE_IMAGE_TAG:-latest}")"
  resources:
    requests:
      memory: "$(yaml_escape "${LLM_SERVICE_MEMORY_REQUEST:-256Mi}")"
      cpu: "$(yaml_escape "${LLM_SERVICE_CPU_REQUEST:-200m}")"
    limits:
      memory: "$(yaml_escape "${LLM_SERVICE_MEMORY_LIMIT:-512Mi}")"
      cpu: "$(yaml_escape "${LLM_SERVICE_CPU_LIMIT:-500m}")"

geocodingService:
  replicas: ${GEOCODING_REPLICAS:-1}
  image:
    tag: "$(yaml_escape "${GEOCODING_IMAGE_TAG:-latest}")"
  resources:
    requests:
      memory: "$(yaml_escape "${GEOCODING_MEMORY_REQUEST:-128Mi}")"
      cpu: "$(yaml_escape "${GEOCODING_CPU_REQUEST:-100m}")"
    limits:
      memory: "$(yaml_escape "${GEOCODING_MEMORY_LIMIT:-256Mi}")"
      cpu: "$(yaml_escape "${GEOCODING_CPU_LIMIT:-200m}")"

poiService:
  replicas: ${POI_REPLICAS:-1}
  image:
    tag: "$(yaml_escape "${POI_IMAGE_TAG:-latest}")"
  resources:
    requests:
      memory: "$(yaml_escape "${POI_MEMORY_REQUEST:-256Mi}")"
      cpu: "$(yaml_escape "${POI_CPU_REQUEST:-200m}")"
    limits:
      memory: "$(yaml_escape "${POI_MEMORY_LIMIT:-512Mi}")"
      cpu: "$(yaml_escape "${POI_CPU_LIMIT:-500m}")"

postgresql:
  enabled: ${POSTGRESQL_ENABLED_VALUE}
  image:
    tag: "$(yaml_escape "${POSTGRESQL_IMAGE_TAG:-16-alpine}")"
  persistence:
    enabled: ${POSTGRESQL_PERSISTENCE_ENABLED_VALUE}
    size: "$(yaml_escape "${POSTGRESQL_STORAGE_SIZE:-1Gi}")"
  resources:
    requests:
      memory: "$(yaml_escape "${POSTGRESQL_MEMORY_REQUEST:-256Mi}")"
      cpu: "$(yaml_escape "${POSTGRESQL_CPU_REQUEST:-250m}")"
    limits:
      memory: "$(yaml_escape "${POSTGRESQL_MEMORY_LIMIT:-512Mi}")"
      cpu: "$(yaml_escape "${POSTGRESQL_CPU_LIMIT:-500m}")"

redis:
  enabled: ${REDIS_ENABLED_VALUE}
  image:
    tag: "$(yaml_escape "${REDIS_IMAGE_TAG:-7-alpine}")"
  persistence:
    enabled: ${REDIS_PERSISTENCE_ENABLED_VALUE}
    size: "$(yaml_escape "${REDIS_STORAGE_SIZE:-1Gi}")"
  resources:
    requests:
      memory: "$(yaml_escape "${REDIS_MEMORY_REQUEST:-128Mi}")"
      cpu: "$(yaml_escape "${REDIS_CPU_REQUEST:-100m}")"
    limits:
      memory: "$(yaml_escape "${REDIS_MEMORY_LIMIT:-256Mi}")"
      cpu: "$(yaml_escape "${REDIS_CPU_LIMIT:-200m}")"

ingress:
  enabled: ${INGRESS_ENABLED_VALUE}
  className: "$(yaml_escape "${INGRESS_CLASS:-nginx}")"
EOF_YAML

cat > "${HELM_SECRETS_FILE}" <<EOF_HELM
secrets:
  dbPassword: "$(yaml_escape "${DB_PASSWORD}")"
  openaiApiKey: "$(yaml_escape "${OPENAI_API_KEY:-}")"
  anthropicApiKey: "$(yaml_escape "${ANTHROPIC_API_KEY:-}")"
  twogisApiKey: "$(yaml_escape "${TWOGIS_API_KEY}")"
  jwtSecret: "$(yaml_escape "${JWT_SECRET_KEY}")"
  encryptionKey: "$(yaml_escape "${ENCRYPTION_KEY}")"
EOF_HELM

echo "✅ Generated ${OUTPUT_FILE} and ${HELM_SECRETS_FILE}"
