param(
    [string]$Driver,
    [string]$EnvPath = "$PSScriptRoot/../.env",
    [switch]$SkipChecks,
    [switch]$SkipBuild,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path "$PSScriptRoot/..\").Path
$script:StepIndex = 0
$script:TotalSteps = 7

function Add-SessionPath {
    param([string[]]$CandidatePaths)

    $added = @()
    foreach ($candidate in $CandidatePaths) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        try {
            $resolved = (Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
        }
        catch {
            continue
        }
        $segments = $env:PATH -split ';' | ForEach-Object { $_.Trim() }
        if (-not ($segments -contains $resolved)) {
            $env:PATH = "$resolved;$env:PATH"
            $added += $resolved
        }
    }

    if ($added.Count -gt 0) {
        Write-Host "💡 Added to PATH for this session:" -ForegroundColor DarkGreen
        foreach ($path in $added) {
            Write-Host "   • $path" -ForegroundColor DarkGreen
        }
        Write-Host
    }
}

function Ensure-ToolPaths {
    $candidates = @(
        "$env:ProgramFiles\\GnuWin32\\bin",
        "$env:ProgramFiles(x86)\\GnuWin32\\bin",
        "$env:ChocolateyInstall\\bin",
        "$env:ProgramFiles\\Git\\usr\\bin",
        "$env:ProgramFiles\\Git\\mingw64\\bin"
    )

    $wingetPackages = Join-Path $env:LOCALAPPDATA 'Microsoft\\WinGet\\Packages'
    if (-not [string]::IsNullOrWhiteSpace($wingetPackages) -and (Test-Path -LiteralPath $wingetPackages)) {
        $gnuWin = Get-ChildItem -Path $wingetPackages -Filter 'GnuWin32.Make*' -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($gnuWin) {
            $candidates += (Join-Path $gnuWin.FullName 'tools')
            $candidates += (Join-Path $gnuWin.FullName 'tools\\bin')
        }
    }

    Add-SessionPath -CandidatePaths $candidates
}

Ensure-ToolPaths

function Show-Welcome {
@'
👋 Welcome! This helper will walk you through:
  1. Verifying every prerequisite and your secret file
  2. Converting the provided .env into Helm-readable YAML
  3. Starting (or reusing) a Minikube cluster
  4. Building all container images inside that cluster
  5. Installing/upgrading the Helm release with waits enabled
  6. Running smoke tests that hit the API gateway
  7. Showing you how to open the site in a browser

Keep this PowerShell window open until the final ✅ appears. The first run downloads a few gigabytes and can take 10–20 minutes.
'@
}

function Write-Step {
    param(
        [string]$Message,
        [string[]]$Details
    )
    $script:StepIndex++
    Write-Host
    Write-Host "🚀 Step $($script:StepIndex)/$($script:TotalSteps): $Message"
    Write-Host "----------------------------------------"
    if ($Details -and $Details.Length -gt 0) {
        foreach ($line in $Details) {
            Write-Host $line
        }
        Write-Host "----------------------------------------"
    }
}

function Write-Warn {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Detect-Driver {
    param([string]$RequestedDriver)
    if (-not [string]::IsNullOrWhiteSpace($RequestedDriver)) {
        return $RequestedDriver
    }
    try {
        $detected = (minikube config get driver 2>$null).Trim()
        if ($detected -and $detected -ne 'not set') {
            return $detected
        }
    } catch {}
    if (Get-Command docker -ErrorAction SilentlyContinue) { return 'docker' }
    if (Get-Command VBoxManage -ErrorAction SilentlyContinue) { return 'virtualbox' }
    if (Get-Command podman -ErrorAction SilentlyContinue) { return 'podman' }
    return 'docker'
}

function Invoke-SetupChecks {
    param([string]$DriverName)
    if (-not $SkipChecks.IsPresent) {
        Write-Step "Running environment diagnostics" @(
            'If something mandatory is missing the script stops now and prints copy-pasteable install commands so you can fix it quickly.'
        )
        & "$PSScriptRoot/setup-check.ps1" -EnvPath $EnvPath -Driver $DriverName
    } else {
        Write-Warn "Skipping setup checks as requested"
    }
}

function Invoke-EnvToYaml {
    Write-Step "Generating Helm values from $EnvPath" @(
        '.env.yaml is written to the repo root for Helm, and helm/ai-tourist/secrets.yaml is refreshed as a chart-local backup.'
    )
    & "$PSScriptRoot/env-to-yaml.ps1" -EnvPath $EnvPath -OutputPath "$RepoRoot/.env.yaml" | Out-Host
}

function Ensure-Minikube {
    param([string]$DriverName)
    Write-Step "Starting Minikube" @(
        'The exact command prints next so you can rerun it manually. Reusing an already running cluster is perfectly fine.'
    )
    try {
        $status = minikube status --format '{{.Host}}' 2>$null
    } catch {
        $status = 'Stopped'
    }
    if ($status -eq 'Running') {
        Write-Info "Minikube already running (driver: $DriverName)"
        return
    }
    $args = @('start', "--driver=$DriverName", '--cpus=6', '--memory=12g')
    if ($DriverName -ne 'none') {
        $args += '--disk-size=40g'
    }
    Write-Host "Command: minikube $($args -join ' ')"
    & minikube @args | Out-Host
    Write-Info "Minikube is running"
}

function Invoke-ImageBuild {
    if ($SkipBuild.IsPresent) {
        Write-Warn "Skipping image build step"
        return
    }
    Write-Step "Building container images" @(
        'Everything builds inside Minikube. No pushes go to Docker Hub. Expect the first build to take a while because it downloads dependencies.'
    )
    $entries = @(
        @{ Dockerfile = 'services/api-gateway/Dockerfile'; Tag = 'ai-tourist-api-gateway:latest'; Context = '.' },
        @{ Dockerfile = 'services/embedding-service/Dockerfile'; Tag = 'ai-tourist-embedding-service:latest'; Context = '.' },
        @{ Dockerfile = 'services/poi-service/Dockerfile'; Tag = 'ai-tourist-poi-service:latest'; Context = '.' },
        @{ Dockerfile = 'services/ranking-service/Dockerfile'; Tag = 'ai-tourist-ranking-service:latest'; Context = '.' },
        @{ Dockerfile = 'services/route-planner-service/Dockerfile'; Tag = 'ai-tourist-route-planner-service:latest'; Context = '.' },
        @{ Dockerfile = 'services/llm-service/Dockerfile'; Tag = 'ai-tourist-llm-service:latest'; Context = '.' },
        @{ Dockerfile = 'services/geocoding-service/Dockerfile'; Tag = 'ai-tourist-geocoding-service:latest'; Context = '.' },
        @{ Dockerfile = 'frontend/Dockerfile'; Tag = 'ai-tourist-frontend:latest'; Context = 'frontend' }
    )

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $dockerEnv = minikube -p minikube docker-env --shell powershell
        Invoke-Expression $dockerEnv
        foreach ($entry in $entries) {
            Write-Host "🔧 Building $($entry.Tag) (Dockerfile $($entry.Dockerfile))"
            & docker build -t $entry.Tag -f "$RepoRoot/$($entry.Dockerfile)" "$RepoRoot/$($entry.Context)" | Out-Host
        }
        $unsetEnv = minikube -p minikube docker-env --shell powershell --unset
        Invoke-Expression $unsetEnv
    }
    else {
        Write-Warn "Docker CLI not found — using 'minikube image build'"
        foreach ($entry in $entries) {
            Write-Host "🔧 Building $($entry.Tag) via Minikube"
            & minikube image build -t $entry.Tag -f "$RepoRoot/$($entry.Dockerfile)" "$RepoRoot/$($entry.Context)" | Out-Host
        }
    }
    Write-Info "Images built"
}

function Invoke-Deploy {
    Write-Step "Deploying Helm chart" @(
        'Helm waits up to 10 minutes for pods to become Ready. Any failure will show right here for quick troubleshooting.'
    )
    & kubectl create namespace ai-tourist 2>$null | Out-Null
    & helm upgrade --install ai-tourist "$RepoRoot/helm/ai-tourist" `
        -n ai-tourist `
        --wait `
        --timeout 10m `
        -f "$RepoRoot/.env.yaml" `
        -f "$RepoRoot/helm/ai-tourist/secrets.yaml" `
        --set ingress.enabled=true `
        --set ingress.host=ai-tourist.local | Out-Host
    Write-Info "Deployment finished"
}

function Invoke-Tests {
    if ($SkipTests.IsPresent) {
        Write-Warn "Skipping smoke tests"
        return
    }
    Write-Step "Running smoke tests" @(
        'Each test spins up a tiny curl pod against the API gateway and prints the JSON response so you can see real traffic.'
    )
    $tests = @(
        @{ Name = 'test-health'; Url = 'http://ai-tourist-api-gateway:8000/health' },
        @{ Name = 'test-ready'; Url = 'http://ai-tourist-api-gateway:8000/ready' },
        @{ Name = 'test-categories'; Url = 'http://ai-tourist-api-gateway:8000/api/v1/categories/list' }
    )
    foreach ($test in $tests) {
        Write-Host "Checking $($test.Name)"
        & kubectl delete pod/$($test.Name) -n ai-tourist --ignore-not-found 2>$null | Out-Null
        & kubectl run $test.Name --restart=Never --image=curlimages/curl -n ai-tourist --command -- sh -c "curl -s $($test.Url)" | Out-Null
        try { & kubectl wait --for=condition=Ready pod/$($test.Name) -n ai-tourist --timeout=60s | Out-Host } catch {}
        Start-Sleep -Seconds 2
        try { & kubectl logs -n ai-tourist $test.Name | jq . | Out-Host } catch { & kubectl logs -n ai-tourist $test.Name | Out-Host }
        & kubectl delete pod/$($test.Name) -n ai-tourist --ignore-not-found 2>$null | Out-Null
    }
    Write-Info "Smoke tests executed"
}

function Show-AccessInfo {
    Write-Step "Cluster access details" @(
        'Pick one of the hosts-file snippets or fall back to kubectl port-forward if hosts edits are locked down.'
    )
    $ip = minikube ip
@"
Add to hosts file:
  $ip ai-tourist.local

Windows (PowerShell as Administrator):
  Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "`n$ip ai-tourist.local"

Windows (Notepad, run as Administrator):
  File → Open → C:\Windows\System32\drivers\etc\hosts → add '$ip ai-tourist.local' on a new line → Save

macOS / Linux / WSL:
  sudo sh -c 'echo "$ip ai-tourist.local" >> /etc/hosts'

Then open: http://ai-tourist.local

Alternative:
  kubectl port-forward -n ai-tourist svc/ai-tourist-frontend 8080:80
  Start-Process "http://localhost:8080" | Out-Null
"@
}

Show-Welcome
$effectiveDriver = Detect-Driver -RequestedDriver $Driver
Invoke-SetupChecks -DriverName $effectiveDriver
Invoke-EnvToYaml
Ensure-Minikube -DriverName $effectiveDriver
Invoke-ImageBuild
Invoke-Deploy
Invoke-Tests
Show-AccessInfo
Write-Info "All steps completed successfully"
