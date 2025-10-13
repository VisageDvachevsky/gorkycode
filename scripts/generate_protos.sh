#!/bin/bash
set -e

PROTO_DIR="proto"
SERVICES=("gateway" "ml" "llm" "routing" "geocoding")

echo "📦 Generating protobuf code for all services..."

for service in "${SERVICES[@]}"; do
    echo "  → Generating for $service service..."
    
    output_dir="services/$service/app/proto"
    mkdir -p "$output_dir"
    
    # Generate Python code from all .proto files
    python -m grpc_tools.protoc \
        -I"$PROTO_DIR" \
        --python_out="$output_dir" \
        --grpc_python_out="$output_dir" \
        "$PROTO_DIR"/*.proto
    
    # Create __init__.py for proto package
    touch "$output_dir/__init__.py"
    
    # Fix imports in generated files (Python 3.11+ style)
    for file in "$output_dir"/*_pb2_grpc.py; do
        if [ -f "$file" ]; then
            sed -i 's/^import \(.*\)_pb2 as/from . import \1_pb2 as/' "$file" 2>/dev/null || \
            sed -i '' 's/^import \(.*\)_pb2 as/from . import \1_pb2 as/' "$file" 2>/dev/null || true
        fi
    done
    
    echo "  ✓ Generated for $service"
done

echo "✅ All protobuf code generated successfully"