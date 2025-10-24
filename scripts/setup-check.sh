#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env"
REQUESTED_DRIVER=""

added_paths=()

add_path_once() {
  local dir="$1"
  if [[ -z "${dir}" || ! -d "${dir}" ]]; then
    return
  fi
  case ":${PATH}:" in
    *:"${dir}":*) return ;;
  esac
  PATH="${dir}:${PATH}"
  added_paths+=("${dir}")
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

  if [[ ${#added_paths[@]} -gt 0 ]]; then
    echo "💡 Added to PATH for this session: ${added_paths[*]}"
    echo
  fi
}

ensure_tool_paths

print_usage() {
  cat <<'USAGE'
Usage: ./scripts/setup-check.sh [options] [ENV_FILE]

Options:
  --driver <name>   Force a specific Minikube driver (docker, virtualbox, hyperv, ...)
  -h, --help        Show this message

If ENV_FILE is not provided the script defaults to .env.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --driver=*)
      REQUESTED_DRIVER="${1#*=}"
      ;;
    --driver)
      shift
      REQUESTED_DRIVER="${1:-}"
      if [[ -z "${REQUESTED_DRIVER}" ]]; then
        echo "❌ --driver requires a value"
        exit 1
      fi
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      ENV_FILE="$1"
      ;;
  esac
  shift
done

detect_driver() {
  local detected
  if [[ -n "${REQUESTED_DRIVER}" ]]; then
    echo "${REQUESTED_DRIVER}"
    return
  fi

  detected="$(minikube config get driver 2>/dev/null || true)"
  if [[ -n "${detected}" && "${detected}" != "not set" ]]; then
    echo "${detected}"
    return
  fi

  echo "docker"
}

EFFECTIVE_DRIVER="$(detect_driver)"

print_header() {
  echo "🔍 AI-Tourist Environment Check"
  echo "================================"
  echo
}

print_install_hint() {
  local tool="$1"
  case "${tool}" in
    minikube)
      cat <<'HINT'
   Install tips:
     • macOS: brew install minikube
     • Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y curl conntrack && curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 && sudo install minikube /usr/local/bin/
     • Windows: run the PowerShell variant of this script (pwsh -File .\scripts\setup-check.ps1) — it prints ready-to-copy winget commands.
     • Windows without Hyper-V: install VirtualBox and start Minikube with --driver=virtualbox.
HINT
      ;;
    kubectl)
      cat <<'HINT'
   Install tips:
     • macOS: brew install kubectl
     • Ubuntu/Debian: sudo apt-get install -y kubectl (or snap install kubectl --classic)
     • Windows: winget install Kubernetes.kubectl (use PowerShell as Administrator)
HINT
      ;;
    helm)
      cat <<'HINT'
   Install tips:
     • macOS: brew install helm
     • Ubuntu/Debian: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
     • Windows: winget install Kubernetes.Helm (or choco install kubernetes-helm)
HINT
      ;;
    docker)
      cat <<'HINT'
   Install tips:
     • macOS/Windows: Docker Desktop (https://www.docker.com/products/docker-desktop/)
     • Windows without Hyper-V: install VirtualBox and run minikube with --driver=virtualbox instead of Docker.
     • Linux: sudo apt-get install -y docker.io OR use minikube image build which works without docker if VirtualBox/Podman is installed.
HINT
      ;;
    VBoxManage)
      cat <<'HINT'
   Install tips:
     • Download VirtualBox from https://www.virtualbox.org/wiki/Downloads
     • Windows users: ensure virtualization is enabled (BIOS > Virtualization Technology) before installing.
     • macOS: brew install --cask virtualbox (requires reboot and security approval).
HINT
      ;;
    podman)
      cat <<'HINT'
   Install tips:
     • macOS: brew install podman && podman machine init && podman machine start
     • Ubuntu/Debian: sudo apt-get install -y podman
     • Windows: install Podman Desktop or use the Docker/VirtualBox driver instead.
HINT
      ;;
    make)
      cat <<'HINT'
   Install tips:
     • macOS: already present with Xcode Command Line Tools (xcode-select --install)
     • Ubuntu/Debian: sudo apt-get install -y make
     • Windows: winget install GnuWin32.Make OR choco install make (optional — scripts can be run without Make).
HINT
      ;;
    jq)
      cat <<'HINT'
   Install tips:
     • macOS: brew install jq
     • Ubuntu/Debian: sudo apt-get install -y jq
     • Windows: winget install jqlang.jq
HINT
      ;;
  esac
}

check_command() {
  local cmd="$1"
  local label="$2"
  local fatal="${3:-false}"
  local hint="${4:-}"
  if command -v "${cmd}" >/dev/null 2>&1; then
    local version
    case "${cmd}" in
      docker)
        version=$(docker --version 2>/dev/null | sed 's/,.*//')
        ;;
      minikube)
        version=$(minikube version --short 2>/dev/null)
        ;;
      kubectl)
        version=$(kubectl version --client --short 2>/dev/null)
        ;;
      helm)
        version=$(helm version --short 2>/dev/null)
        ;;
      make)
        version=$(make --version 2>/dev/null | head -n1)
        ;;
      jq)
        version=$(jq --version 2>/dev/null)
        ;;
      *)
        version="installed"
        ;;
    esac
    echo "✅ ${label}: ${version}"
  else
    if [[ "${fatal}" == "true" ]]; then
      echo "❌ ${label} is not installed"
      HAS_ERRORS=1
      [[ -n "${hint}" ]] && print_install_hint "${hint}"
    else
      echo "⚠️  ${label} not found"
      [[ -n "${hint}" ]] && print_install_hint "${hint}"
    fi
  fi
}

check_env_file() {
  echo
  echo "📄 Checking environment file..."
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "❌ ${ENV_FILE} not found"
    HAS_ERRORS=1
    cat <<'HINT'
   Fix it:
     • Copy the provided .env from the archive into the repository root (cp /path/to/archive/.env ./.env)
     • Or duplicate .env.example and fill in the secrets manually (cp .env.example .env)
HINT
    return
  fi

  echo "✅ ${ENV_FILE} found"

  # shellcheck disable=SC1090
  source "${ENV_FILE}"

  if [[ -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "⚠️  No LLM API key configured (OPENAI_API_KEY or ANTHROPIC_API_KEY)"
  else
    echo "✅ LLM API key configured"
  fi

  if [[ -z "${TWOGIS_API_KEY:-}" ]]; then
    echo "⚠️  TWOGIS_API_KEY not configured"
  else
    echo "✅ 2GIS API key configured"
  fi
}

check_project_layout() {
  echo
  echo "📁 Checking project layout..."

  local required=("proto" "services" "helm/ai-tourist" "scripts")
  for path in "${required[@]}"; do
    if [[ -e "${path}" ]]; then
      echo "✅ ${path} present"
    else
      echo "❌ ${path} missing"
      HAS_ERRORS=1
    fi
  done
}

check_disk_space() {
  echo
  echo "💾 Checking disk space..."
  local available_gb
  available_gb=$(df -BG . | tail -n1 | awk '{print $4}' | sed 's/G//')
  if [[ -z "${available_gb}" ]]; then
    echo "⚠️  Unable to determine disk space"
    return
  fi

  if (( available_gb < 20 )); then
    echo "⚠️  Low disk space (${available_gb}GB available). Recommended: 20GB+"
    cat <<'HINT'
   Free up space by:
     • Deleting old Docker/Minikube images: minikube delete && docker system prune -af
     • Removing unused downloads or moving them to an external drive
     • Increasing the VM disk if running inside a virtual machine
HINT
  else
    echo "✅ ${available_gb}GB available"
  fi
}

print_footer() {
  echo
  echo "================================"
  if (( HAS_ERRORS > 0 )); then
    echo "❌ Setup check failed"
    echo "Please resolve the errors above before deploying."
    exit 1
  else
    echo "✅ Setup check passed"
    echo "Next steps:"
    local driver_hint
    driver_hint="${REQUESTED_DRIVER:-${EFFECTIVE_DRIVER}}"
    echo "  • ./scripts/judge-run.sh --driver=${driver_hint}"
    echo "    or"
    echo "  • pwsh -File .\\scripts\\judge-run.ps1 -Driver ${driver_hint}"
    echo ""
    echo "The judge-run helper script will convert .env, start Minikube, build images and deploy the chart automatically."
  fi
}

HAS_ERRORS=0

print_header

echo "📦 Checking dependencies..."
check_command minikube "Minikube" true minikube
check_command kubectl "kubectl" true kubectl
check_command helm "Helm" true helm
check_command make "GNU Make" false make
check_command jq "jq" false jq

check_driver_dependencies() {
  echo
  echo "🛞 Minikube driver: ${EFFECTIVE_DRIVER}"
  case "${EFFECTIVE_DRIVER}" in
    docker|docker-containerd|cri-dockerd)
      check_command docker "Docker" true docker
      ;;
    podman)
      check_command podman "Podman" true podman
      ;;
    virtualbox)
      check_command VBoxManage "VirtualBox" true VBoxManage
      ;;
    hyperkit)
      check_command hyperkit "HyperKit" true
      ;;
    kvm2)
      if command -v virsh >/dev/null 2>&1; then
        echo "✅ libvirt (virsh) installed"
      else
        echo "⚠️  libvirt (virsh) not found — ensure KVM is installed"
      fi
      ;;
    hyperv)
      echo "ℹ️ Using Hyper-V. Run this script from an elevated PowerShell if you need to manage switches."
      ;;
    none)
      echo "⚠️  Driver 'none' requires running Minikube with sudo on Linux."
      ;;
    *)
      echo "⚠️  Unknown driver '${EFFECTIVE_DRIVER}'. Ensure the required hypervisor/runtime is installed."
      ;;
  esac
  echo "   Override driver: ./scripts/setup-check.sh --driver=<name>"
}

check_virtualization() {
  echo
  echo "🧠 Checking hardware virtualization..."
  case "$(uname -s)" in
    Linux)
      if command -v lscpu >/dev/null 2>&1; then
        local virt
        virt="$(lscpu | awk -F: '/Virtualization:/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')"
        if [[ -n "${virt}" ]]; then
          echo "✅ Hardware virtualization detected (${virt})"
        else
          echo "⚠️  Unable to confirm virtualization from lscpu. Ensure VT-x/AMD-V is enabled in BIOS."
          cat <<'HINT'
   Typical steps:
     1. Reboot and enter BIOS/UEFI (keys: F2, F10, Delete depending on vendor).
     2. Locate “Intel Virtualization Technology”, “VT-x”, or “SVM Mode” and set it to Enabled.
     3. Save changes, boot back into the OS, then rerun this script.
HINT
        fi
      else
        echo "⚠️  lscpu not available to verify virtualization support."
      fi
      ;;
    Darwin)
      if [[ "$(sysctl -n kern.hv_support 2>/dev/null || echo 0)" == "1" ]]; then
        echo "✅ Apple Hypervisor framework is available"
      else
        echo "⚠️  Hypervisor framework disabled. Enable Virtualization in System Settings > General > Sharing."
        cat <<'HINT'
   On Apple Silicon Macs you may also need to allow virtualization for the terminal app:
     • System Settings → Privacy & Security → Developer Tools → enable for Terminal/iTerm.
   After toggling, reboot and run the script again.
HINT
      fi
      ;;
    *)
      echo "ℹ️ Run the PowerShell version of this script on Windows for virtualization diagnostics."
      ;;
  esac
}

build_minikube_command() {
  local base="minikube start --driver=${EFFECTIVE_DRIVER} --cpus=6 --memory=12g"
  case "${EFFECTIVE_DRIVER}" in
    docker|docker-containerd|cri-dockerd|podman|virtualbox|hyperkit|hyperv|kvm2)
      echo "${base} --disk-size=40g"
      ;;
    none)
      echo "sudo ${base}"
      ;;
    *)
      echo "${base} --disk-size=40g"
      ;;
  esac
}

MINIKUBE_START_CMD="$(build_minikube_command)"

check_env_file
check_project_layout
check_disk_space
check_driver_dependencies
check_virtualization
print_footer
