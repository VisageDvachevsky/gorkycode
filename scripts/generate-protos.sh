#!/bin/bash
set -e

PROTO_DIR="proto"
SERVICES=(
  "api-gateway"
  "embedding-service"
  "ranking-service"
  "route-planner-service"
  "llm-service"
  "geocoding-service"
  "poi-service"
)

echo "🔧 Generating gRPC code from proto files..."

for service in "${SERVICES[@]}"; do
  SERVICE_DIR="services/$service"
  
  if [ ! -d "$SERVICE_DIR" ]; then
    echo "⚠️  Service directory not found: $SERVICE_DIR"
    continue
  fi
  
  echo "  → Generating for $service..."
  
  mkdir -p "$SERVICE_DIR/app/proto"
  
  python -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$SERVICE_DIR/app/proto" \
    --grpc_python_out="$SERVICE_DIR/app/proto" \
    --pyi_out="$SERVICE_DIR/app/proto" \
    "$PROTO_DIR"/*.proto
  
  touch "$SERVICE_DIR/app/proto/__init__.py"
  
  for file in "$SERVICE_DIR/app/proto"/*_pb2*.py; do
    if [ -f "$file" ]; then
      sed -i 's/^import \(.*\)_pb2/from . import \1_pb2/' "$file"
    fi
  done
  
  echo "    ✓ Generated for $service"
done

echo "✅ Proto generation complete!"