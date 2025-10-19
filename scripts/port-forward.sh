#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-ai-tourist}"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required for port-forwarding" >&2
  exit 1
fi

for svc in ai-tourist-frontend ai-tourist-api-gateway; do
  if ! kubectl get svc "$svc" -n "$NAMESPACE" >/dev/null 2>&1; then
    echo "Service $svc not found in namespace $NAMESPACE" >&2
    exit 1
  fi
done

FRONTEND_PID=""
API_PID=""

cleanup() {
  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting port-forwarding for AI Tourist..."

echo "Forwarding frontend service to http://localhost:8080"
kubectl port-forward -n "$NAMESPACE" --address 0.0.0.0 svc/ai-tourist-frontend 8080:80 &
FRONTEND_PID=$!

sleep 1

echo "Forwarding API gateway service to http://localhost:8000"
kubectl port-forward -n "$NAMESPACE" --address 0.0.0.0 svc/ai-tourist-api-gateway 8000:8000 &
API_PID=$!

sleep 1

echo ""
echo "Port-forwarding active. Use Ctrl+C to stop."
echo "  Frontend:  http://localhost:8080"
echo "  API:       http://localhost:8000"
echo ""

wait "$FRONTEND_PID" "$API_PID"
