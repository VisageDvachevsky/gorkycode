#!/bin/bash

# Скрипт для проверки сгенерированного values.yaml

set -e

ENV_YAML="values.yaml"
VALUES_YAML="helm/ai-tourist/values.yaml"

echo "🔍 Validation Script for values.yaml"
echo "=================================="
echo ""

# Check if files exist
if [ ! -f "$ENV_YAML" ]; then
  echo "❌ $ENV_YAML not found!"
  echo "   Run ./generate-env-yaml.sh first"
  exit 1
fi

if [ ! -f "$VALUES_YAML" ]; then
  echo "⚠️  $VALUES_YAML not found!"
  echo "   This script works best with values.yaml present"
  echo ""
fi

# Function to check if key exists in yaml
check_structure() {
  echo "📋 Checking YAML structure..."
  
  # Check main sections
  sections=(
    "global"
    "secrets"
    "llm"
    "frontend"
    "apiGateway"
    "embeddingService"
    "rankingService"
    "routePlannerService"
    "llmService"
    "geocodingService"
    "poiService"
    "postgresql"
    "redis"
    "ingress"
  )
  
  missing=()
  found=()
  
  for section in "${sections[@]}"; do
    if grep -q "^${section}:" "$ENV_YAML"; then
      found+=("$section")
    else
      missing+=("$section")
    fi
  done
  
  if [ ${#found[@]} -gt 0 ]; then
    echo "✅ Found sections (${#found[@]}):"
    for s in "${found[@]}"; do
      echo "   - $s"
    done
    echo ""
  fi
  
  if [ ${#missing[@]} -gt 0 ]; then
    echo "⚠️  Missing sections (${#missing[@]}):"
    for s in "${missing[@]}"; do
      echo "   - $s"
    done
    echo "   (This is OK if using defaults from values.yaml)"
    echo ""
  fi
}

# Function to check for old structure patterns
check_old_patterns() {
  echo "🔍 Checking for old structure patterns..."
  
  old_patterns=(
    "scaling:"
    "resources: *# at root level"
    "gateway: *# should be apiGateway"
    "embedding: *# should be embeddingService"
    "monitoring:"
  )
  
  found_old=false
  
  if grep -q "^scaling:" "$ENV_YAML"; then
    echo "❌ Found old 'scaling:' section (should be removed)"
    found_old=true
  fi
  
  if grep -q "^resources:" "$ENV_YAML"; then
    echo "❌ Found old 'resources:' at root level (should be nested in services)"
    found_old=true
  fi
  
  if grep -q "^monitoring:" "$ENV_YAML"; then
    echo "⚠️  Found 'monitoring:' section (not in current values.yaml)"
    found_old=true
  fi
  
  if grep -q "gateway:" "$ENV_YAML" && ! grep -q "apiGateway:" "$ENV_YAML"; then
    echo "❌ Found 'gateway:' instead of 'apiGateway:'"
    found_old=true
  fi
  
  if ! $found_old; then
    echo "✅ No old structure patterns found"
  fi
  echo ""
}

# Function to validate secrets
check_secrets() {
  echo "🔐 Checking secrets..."
  
  secrets=(
    "dbPassword"
    "openaiApiKey"
    "anthropicApiKey"
    "twogisApiKey"
    "jwtSecret"
    "encryptionKey"
  )
  
  warnings=()
  
  for secret in "${secrets[@]}"; do
    value=$(grep -A 1 "secrets:" "$ENV_YAML" | grep "$secret:" | cut -d'"' -f2 || echo "")
    
    if [ -z "$value" ]; then
      warnings+=("$secret is empty")
    elif [[ "$value" == *"dev_"* ]] || [[ "$value" == *"generate_"* ]] || [[ "$value" == *"change_in_production"* ]]; then
      warnings+=("$secret has placeholder value: $value")
    fi
  done
  
  if [ ${#warnings[@]} -eq 0 ]; then
    echo "✅ All secrets configured"
  else
    echo "⚠️  Secret warnings:"
    for w in "${warnings[@]}"; do
      echo "   - $w"
    done
  fi
  echo ""
}

# Function to check service structure
check_service_structure() {
  echo "🔧 Checking service structure..."
  
  services=(
    "frontend"
    "apiGateway"
    "embeddingService"
    "rankingService"
    "routePlannerService"
    "llmService"
    "geocodingService"
    "poiService"
  )
  
  for service in "${services[@]}"; do
    if grep -q "^${service}:" "$ENV_YAML"; then
      has_replicas=$(grep -A 10 "^${service}:" "$ENV_YAML" | grep -c "replicas:" || echo "0")
      has_resources=$(grep -A 20 "^${service}:" "$ENV_YAML" | grep -c "resources:" || echo "0")
      has_image=$(grep -A 15 "^${service}:" "$ENV_YAML" | grep -c "image:" || echo "0")
      
      status="✅"
      details=""
      
      if [ "$has_replicas" -eq 0 ]; then
        status="⚠️ "
        details="${details} missing replicas"
      fi
      
      if [ "$has_resources" -eq 0 ]; then
        status="⚠️ "
        details="${details} missing resources"
      fi
      
      echo "$status $service$details"
    fi
  done
  echo ""
}

# Function to estimate resource usage
estimate_resources() {
  echo "📊 Estimating total resource requests..."
  
  # Extract memory values
  memory_values=$(grep -E "memory:.*Mi|memory:.*Gi" "$ENV_YAML" | grep "requests:" -A 1 | grep "memory:" | awk '{print $2}' | tr -d '"' || echo "")
  
  total_memory_mi=0
  total_memory_gi=0
  
  while IFS= read -r mem; do
    if [[ "$mem" == *"Gi" ]]; then
      val=$(echo "$mem" | sed 's/Gi//')
      total_memory_gi=$(echo "$total_memory_gi + $val" | bc)
    elif [[ "$mem" == *"Mi" ]]; then
      val=$(echo "$mem" | sed 's/Mi//')
      total_memory_mi=$(echo "$total_memory_mi + $val" | bc)
    fi
  done <<< "$memory_values"
  
  # Convert to Gi
  total_gi=$(echo "scale=2; $total_memory_gi + ($total_memory_mi / 1024)" | bc)
  
  echo "   Total memory requests: ~${total_gi}Gi"
  
  if (( $(echo "$total_gi > 8" | bc -l) )); then
    echo "   ⚠️  High memory usage - ensure your cluster has sufficient resources"
  else
    echo "   ✅ Reasonable memory usage"
  fi
  echo ""
}

# Run all checks
check_structure
check_old_patterns
check_secrets
check_service_structure
estimate_resources

# Final summary
echo "=================================="
echo "Summary:"
echo "=================================="

if [ -f "$VALUES_YAML" ]; then
  echo "📝 To apply configuration:"
  echo "   helm upgrade ai-tourist ./helm/ai-tourist -f $ENV_YAML"
  echo ""
  echo "📝 To see what will be deployed:"
  echo "   helm template ai-tourist ./helm/ai-tourist -f $ENV_YAML"
  echo ""
  echo "📝 To see differences:"
  echo "   helm diff upgrade ai-tourist ./helm/ai-tourist -f $ENV_YAML"
else
  echo "📝 Validate with your values.yaml:"
  echo "   helm template ai-tourist /path/to/helm/ai-tourist -f $ENV_YAML"
fi

echo ""
echo "✅ Validation complete!"