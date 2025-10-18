#!/bin/bash
set -e

# Script to generate Helm ConfigMap for POI data
# Usage: ./scripts/generate-poi-configmap.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
POI_JSON="$PROJECT_ROOT/data/poi.json"
OUTPUT_FILE="$PROJECT_ROOT/helm/ai-tourist/templates/configmap-poi-data.yaml"

echo "🔧 Generating POI data ConfigMap for Helm..."
echo "   Source: $POI_JSON"
echo "   Output: $OUTPUT_FILE"

if [ ! -f "$POI_JSON" ]; then
    echo "❌ Error: POI data file not found: $POI_JSON"
    exit 1
fi

# Check file size (ConfigMaps have 1MB limit)
POI_SIZE=$(stat -f%z "$POI_JSON" 2>/dev/null || stat -c%s "$POI_JSON")
POI_SIZE_MB=$(echo "scale=2; $POI_SIZE / 1024 / 1024" | bc)

if (( $(echo "$POI_SIZE > 900000" | bc -l) )); then
    echo "⚠️  Warning: POI file is large ($POI_SIZE_MB MB). ConfigMap limit is 1MB."
    echo "   Consider using PersistentVolume instead."
fi

cat > "$OUTPUT_FILE" << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "ai-tourist.fullname" . }}-poi-data
  labels:
    {{- include "ai-tourist.labels" . | nindent 4 }}
    app.kubernetes.io/component: data
data:
  poi.json: |
EOF

# Indent JSON content by 4 spaces
sed 's/^/    /' "$POI_JSON" >> "$OUTPUT_FILE"

echo ""
echo "✅ ConfigMap generated successfully!"
echo "   Size: $POI_SIZE_MB MB"
echo "   Location: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "  1. Review the generated file"
echo "  2. helm upgrade --install ai-tourist ./helm/ai-tourist"
echo "  3. The post-install Job will load POI data automatically"