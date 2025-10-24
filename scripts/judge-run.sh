#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./scripts/judge-run.sh [options]

Options:
  --driver <name>       Override Minikube driver (docker, virtualbox, hyperv, ...)
  --env <path>          Path to the .env file (default: ./.env)
  --skip-checks         Skip running setup-check (assumes dependencies ready)
  --skip-build          Skip building container images
  --skip-tests          Skip post-deploy smoke tests
  --help                Show this message
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
DRIVER=""
RUN_CHECKS=true
RUN_BUILD=true
RUN_TESTS=true
CURRENT_STEP=0
TOTAL_STEPS=7

declare -a ADDED_PATHS=()

add_path_once() {
  local dir="$1"
  if [[ -z "${dir}" || ! -d "${dir}" ]]; then
    return
  fi
  case ":${PATH}:" in
    *:"${dir}":*) return ;;
  esac
  PATH="${dir}:${PATH}"
  ADDED_PATHS+=("${dir}")
}

ensure_tool_paths() {
  add_path_once "${HOME}/.local/bin"
  add_path_once "/usr/local/bin"
  add_path_once "/opt/homebrew/bin"

  if [[ -d "/usr/local/opt/make/libexec/gnubin" ]]; then
    add_path_once "/usr/local/opt/make/libexec/gnubin"
  fi
  if [[ -d "/opt/homebrew/opt/make/libexec/gnubin" ]]; then
    add_path_once "/opt/homebrew/opt/make/libexec/gnubin"
  fi

  if command -v brew >/dev/null 2>&1; then
    local brew_make_prefix
    brew_make_prefix="$(brew --prefix make 2>/dev/null || true)"
    if [[ -n "${brew_make_prefix}" ]]; then
      add_path_once "${brew_make_prefix}/libexec/gnubin"
    fi
  fi

  if [[ ${#ADDED_PATHS[@]} -gt 0 ]]; then
    echo "💡 Added to PATH for this session: ${ADDED_PATHS[*]}"
    echo
  fi
}

ensure_tool_paths

while [[ $# -gt 0 ]]; do
  case "$1" in
    --driver)
      shift
      DRIVER="${1:-}"
      [[ -n "${DRIVER}" ]] || { echo "❌ --driver requires a value"; exit 1; }
      ;;
    --driver=*)
      DRIVER="${1#*=}"
      ;;
    --env)
      shift
      ENV_FILE="${1:-}"
      [[ -n "${ENV_FILE}" ]] || { echo "❌ --env requires a value"; exit 1; }
      ;;
    --env=*)
      ENV_FILE="${1#*=}"
      ;;
    --skip-checks)
      RUN_CHECKS=false
      ;;
    --skip-build)
      RUN_BUILD=false
      ;;
    --skip-tests)
      RUN_TESTS=false
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "❌ Unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift

done

welcome_message() {
  cat <<'WELCOME'
👋 Welcome! This helper will walk you through:
  1. Verifying every prerequisite and your secret file
  2. Converting the provided .env into Helm-readable YAML
  3. Starting (or reusing) a Minikube cluster
  4. Building all container images inside that cluster
  5. Installing/upgrading the Helm release with waits enabled
  6. Running smoke tests that hit the API gateway
  7. Showing you how to open the site in a browser

Keep this window open until you see the final ✅ message. The first run often downloads a few gigabytes and can take 10–20 minutes.
WELCOME
}

log_step() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  echo
  echo "🚀 Step ${CURRENT_STEP}/${TOTAL_STEPS}: $1"
  echo "----------------------------------------"
}

warn() {
  echo "⚠️  $1"
}

info() {
  echo "✅ $1"
}

error_exit() {
  echo "❌ $1"
  exit 1
}

detect_driver() {
  if [[ -n "${DRIVER}" ]]; then
    echo "${DRIVER}"
    return
  fi
  local detected
  detected="$(minikube config get driver 2>/dev/null || true)"
  if [[ -n "${detected}" && "${detected}" != "not set" ]]; then
    echo "${detected}"
    return
  fi
  if command -v docker >/dev/null 2>&1; then
    echo "docker"
  elif command -v VBoxManage >/dev/null 2>&1; then
    echo "virtualbox"
  elif command -v podman >/dev/null 2>&1; then
    echo "podman"
  else
    echo "docker"
  fi
}

run_checks() {
  if [[ "${RUN_CHECKS}" == "true" ]]; then
    log_step "Running environment diagnostics"
    cat <<'DETAILS'
If something mandatory is missing the script stops now and prints copy-pasteable install commands so you can fix it quickly.
DETAILS
    "${SCRIPT_DIR}/setup-check.sh" ${DRIVER:+--driver "${DRIVER}"} "${ENV_FILE}"
  else
    warn "Skipping setup checks as requested"
  fi
}

prepare_env() {
  log_step "Generating Helm values from ${ENV_FILE}"
  cat <<'DETAILS'
Outputs:
  • .env.yaml in the repository root (consumed by Helm automatically)
  • helm/ai-tourist/secrets.yaml (handy backup inside the chart)
DETAILS
  "${SCRIPT_DIR}/env-to-yaml.sh" "${ENV_FILE}" "${REPO_ROOT}/.env.yaml"
}

minikube_start() {
  log_step "Starting Minikube"
  cat <<'DETAILS'
The exact command appears below so you can re-run it manually. Reusing an already running cluster is perfectly fine.
DETAILS
  local driver
  driver="$(detect_driver)"
  local base_cmd=(minikube start "--driver=${driver}" --cpus=6 --memory=12g)
  if [[ "${driver}" != "none" ]]; then
    base_cmd+=(--disk-size=40g)
  else
    base_cmd=(sudo "${base_cmd[@]}")
  fi
  if minikube status >/dev/null 2>&1; then
    info "Minikube already running (driver: ${driver})"
    return
  fi
  echo "Command: ${base_cmd[*]}"
  "${base_cmd[@]}"
  info "Minikube is running"
}

build_images() {
  if [[ "${RUN_BUILD}" != "true" ]]; then
    warn "Skipping image build step"
    return
  fi
  log_step "Building container images"
  cat <<'DETAILS'
All builds happen inside Minikube. Nothing pushes to Docker Hub. The first build is slow; subsequent runs reuse the cached layers.
DETAILS
  local docker_available=false
  if command -v docker >/dev/null 2>&1; then
    docker_available=true
  fi
  local entries=(
    "services/api-gateway/Dockerfile ai-tourist-api-gateway:latest ."
    "services/embedding-service/Dockerfile ai-tourist-embedding-service:latest ."
    "services/poi-service/Dockerfile ai-tourist-poi-service:latest ."
    "services/ranking-service/Dockerfile ai-tourist-ranking-service:latest ."
    "services/route-planner-service/Dockerfile ai-tourist-route-planner-service:latest ."
    "services/llm-service/Dockerfile ai-tourist-llm-service:latest ."
    "services/geocoding-service/Dockerfile ai-tourist-geocoding-service:latest ."
    "frontend/Dockerfile ai-tourist-frontend:latest frontend"
  )

  if [[ "${docker_available}" == "true" ]]; then
    eval "$(minikube -p minikube docker-env)"
    for entry in "${entries[@]}"; do
      read -r dockerfile tag context <<<"${entry}"
      echo "🔧 Building ${tag} (Dockerfile ${dockerfile})"
      docker build -t "${tag}" -f "${REPO_ROOT}/${dockerfile}" "${REPO_ROOT}/${context}"
    done
    eval "$(minikube -p minikube docker-env -u)"
  else
    warn "Docker CLI not found — using 'minikube image build'"
    for entry in "${entries[@]}"; do
      read -r dockerfile tag context <<<"${entry}"
      echo "🔧 Building ${tag} via Minikube"
      minikube image build -t "${tag}" -f "${REPO_ROOT}/${dockerfile}" "${REPO_ROOT}/${context}"
    done
  fi
  info "Images built"
}

deploy_chart() {
  log_step "Deploying Helm chart"
  cat <<'DETAILS'
Helm waits up to 10 minutes for everything to become Ready. If a pod fails you will see the error text right here.
DETAILS
  kubectl create namespace ai-tourist 2>/dev/null || true
  helm upgrade --install ai-tourist "${REPO_ROOT}/helm/ai-tourist" \
    -n ai-tourist \
    --wait \
    --timeout 10m \
    -f "${REPO_ROOT}/.env.yaml" \
    -f "${REPO_ROOT}/helm/ai-tourist/secrets.yaml" \
    --set ingress.enabled=true \
    --set ingress.host=ai-tourist.local
  info "Deployment finished"
}

run_tests() {
  if [[ "${RUN_TESTS}" != "true" ]]; then
    warn "Skipping smoke tests"
    return
  fi
  log_step "Running smoke tests"
  cat <<'DETAILS'
Each test spins up a tiny curl pod that calls the API gateway. Successful JSON payloads are printed so you see real data flowing.
DETAILS
  local namespace="ai-tourist"
  local tests=(
    "test-health http://ai-tourist-api-gateway:8000/health"
    "test-ready http://ai-tourist-api-gateway:8000/ready"
    "test-categories http://ai-tourist-api-gateway:8000/api/v1/categories/list"
  )
  for test in "${tests[@]}"; do
    read -r name url <<<"${test}"
    echo "Checking ${name}"
    kubectl delete pod/${name} -n "${namespace}" --ignore-not-found >/dev/null 2>&1 || true
    kubectl run "${name}" --restart=Never --image=curlimages/curl -n "${namespace}" --command -- sh -c "curl -s ${url}" >/dev/null
    kubectl wait --for=condition=Ready pod/"${name}" -n "${namespace}" --timeout=60s >/dev/null 2>&1 || true
    sleep 2
    kubectl logs -n "${namespace}" "${name}" | jq . || true
    kubectl delete pod/"${name}" -n "${namespace}" --ignore-not-found >/dev/null 2>&1 || true
  done
  info "Smoke tests executed"
}

show_url() {
  log_step "Cluster access details"
  cat <<'DETAILS'
Choose one of the hosts-file snippets or fall back to kubectl port-forward if editing hosts is locked down by corporate policy.
DETAILS
  local host="ai-tourist.local"
  local ip
  ip="$(minikube ip)"
  cat <<EOF
Add to hosts file:
  ${ip} ${host}

macOS / Linux:
  sudo sh -c 'echo "${ip} ${host}" >> /etc/hosts'

Windows (PowerShell as Administrator):
  Add-Content -Path C:\\Windows\\System32\\drivers\\etc\\hosts -Value "`n${ip} ${host}"

Windows (Notepad, run as Administrator):
  File → Open → C:\\Windows\\System32\\drivers\\etc\\hosts → add '${ip} ${host}' on a new line → Save

Then open: http://${host}

Alternative:
  kubectl port-forward -n ai-tourist svc/ai-tourist-frontend 8080:80
  open http://localhost:8080
EOF
}

welcome_message
run_checks
prepare_env
minikube_start
build_images
deploy_chart
run_tests
show_url

info "All steps completed successfully"
