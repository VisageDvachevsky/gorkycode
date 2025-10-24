param(
    [string]$EnvPath = ".env",
    [string]$Driver
)

$ErrorCount = 0

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

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

function Show-InstallHint {
    param([string]$Tool)
    switch ($Tool) {
        'minikube' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • winget install Kubernetes.minikube" -ForegroundColor DarkCyan
            Write-Host "     • Or download the installer: https://minikube.sigs.k8s.io/docs/start/" -ForegroundColor DarkCyan
            Write-Host "     • Windows Home without Hyper-V: install VirtualBox and run with -Driver virtualbox" -ForegroundColor DarkCyan
        }
        'kubectl' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • winget install Kubernetes.kubectl" -ForegroundColor DarkCyan
            Write-Host "     • Or download from https://kubernetes.io/docs/tasks/tools/" -ForegroundColor DarkCyan
        }
        'helm' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • winget install Kubernetes.Helm" -ForegroundColor DarkCyan
            Write-Host "     • Or use Chocolatey: choco install kubernetes-helm" -ForegroundColor DarkCyan
        }
        'docker' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • Download Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor DarkCyan
            Write-Host "     • If Hyper-V/WSL2 are unavailable, install VirtualBox and use -Driver virtualbox" -ForegroundColor DarkCyan
        }
        'virtualbox' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • Download VirtualBox: https://www.virtualbox.org/wiki/Downloads" -ForegroundColor DarkCyan
            Write-Host "     • Enable virtualization in BIOS/UEFI before installing." -ForegroundColor DarkCyan
        }
        'podman' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • Install Podman Desktop: https://podman-desktop.io/" -ForegroundColor DarkCyan
            Write-Host "     • Or rely on Docker/VirtualBox drivers instead." -ForegroundColor DarkCyan
        }
        'make' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • winget install GnuWin32.Make  (optional)" -ForegroundColor DarkCyan
            Write-Host "     • Or choco install make" -ForegroundColor DarkCyan
            Write-Host "     • You can also run pwsh -File .\\scripts\\judge-run.ps1 without installing make." -ForegroundColor DarkCyan
            Write-Host "     • This script temporarily adds common install paths (GnuWin32/Chocolatey) to PATH automatically." -ForegroundColor DarkCyan
        }
        'jq' {
            Write-Host "   Install tips:" -ForegroundColor DarkCyan
            Write-Host "     • winget install jqlang.jq" -ForegroundColor DarkCyan
            Write-Host "     • Or download jq.exe and place it in PATH: https://jqlang.github.io/jq/download/" -ForegroundColor DarkCyan
        }
    }
}

function Test-CommandInstalled {
    param(
        [string]$Command,
        [string]$Label,
        [bool]$Required = $false,
        [ScriptBlock]$VersionScript = $null,
        [string]$HintTool
    )
    $cmd = Get-Command $Command -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        if ($null -ne $VersionScript) {
            $version = & $VersionScript
            Write-Host "✅ $Label: $version"
        }
        else {
            Write-Host "✅ $Label installed"
        }
    }
    else {
        $toolName = if ([string]::IsNullOrWhiteSpace($HintTool)) { $Command } else { $HintTool }
        if ($Required) {
            Write-ErrorMessage "❌ $Label is not installed"
            $script:ErrorCount += 1
            Show-InstallHint -Tool $toolName
        }
        else {
            Write-WarningMessage "⚠️  $Label not found"
            Show-InstallHint -Tool $toolName
        }
    }
}

function Parse-EnvFile {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $result
    }
    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq '' -or $line.StartsWith('#')) { return }
        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) { return }
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.StartsWith('"') -and $value.EndsWith('"') -and $value.Length -ge 2) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($value.StartsWith("'") -and $value.EndsWith("'") -and $value.Length -ge 2) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $result[$key] = $value
    }
    return $result
}

function Get-EffectiveDriver {
    param([string]$RequestedDriver)
    if (-not [string]::IsNullOrWhiteSpace($RequestedDriver)) {
        return $RequestedDriver
    }
    try {
        $detected = (minikube config get driver 2>$null).Trim()
        if ($detected -and $detected -ne 'not set') {
            return $detected
        }
    }
    catch {
    }
    return 'docker'
}

$EffectiveDriver = Get-EffectiveDriver -RequestedDriver $Driver

function Get-MinKubeStartCommand {
    param([string]$DriverName)
    $base = "minikube start --driver=$DriverName --cpus=6 --memory=12g"
    switch ($DriverName) {
        'docker' { return "$base --disk-size=40g" }
        'docker-containerd' { return "$base --disk-size=40g" }
        'cri-dockerd' { return "$base --disk-size=40g" }
        'podman' { return "$base --disk-size=40g" }
        'virtualbox' { return "$base --disk-size=40g" }
        'hyperkit' { return "$base --disk-size=40g" }
        'hyperv' { return "$base --disk-size=40g" }
        'kvm2' { return "$base --disk-size=40g" }
        'none' { return "$base" }
        default { return "$base --disk-size=40g" }
    }
}

$MinikubeStartCommand = Get-MinKubeStartCommand -DriverName $EffectiveDriver

Write-Host "🔍 AI-Tourist Environment Check"
Write-Host "================================"
Write-Host

Write-Info "📦 Checking dependencies..."
Test-CommandInstalled -Command 'minikube' -Label 'Minikube' -Required $true -VersionScript { minikube version --short } -HintTool 'minikube'
Test-CommandInstalled -Command 'kubectl' -Label 'kubectl' -Required $true -VersionScript { kubectl version --client --short } -HintTool 'kubectl'
Test-CommandInstalled -Command 'helm' -Label 'Helm' -Required $true -VersionScript { helm version --short } -HintTool 'helm'
Test-CommandInstalled -Command 'make' -Label 'GNU Make' -Required $false -VersionScript { (make --version | Select-Object -First 1) } -HintTool 'make'
Test-CommandInstalled -Command 'jq' -Label 'jq' -Required $false -VersionScript { jq --version } -HintTool 'jq'

Write-Host
Write-Info "📄 Checking environment file..."
if (-not (Test-Path -LiteralPath $EnvPath)) {
    Write-ErrorMessage "❌ $EnvPath not found"
    $ErrorCount += 1
    Write-Host "   Fix it:" -ForegroundColor DarkCyan
    Write-Host "     • Copy the provided .env from the archive into the repo root" -ForegroundColor DarkCyan
    Write-Host "     • Or duplicate .env.example and populate the secrets (cp .env.example .env)" -ForegroundColor DarkCyan
}
else {
    Write-Host "✅ $EnvPath found"
    $envValues = Parse-EnvFile -Path $EnvPath
    if ((-not $envValues.ContainsKey('OPENAI_API_KEY') -or [string]::IsNullOrWhiteSpace($envValues['OPENAI_API_KEY'])) -and (-not $envValues.ContainsKey('ANTHROPIC_API_KEY') -or [string]::IsNullOrWhiteSpace($envValues['ANTHROPIC_API_KEY']))) {
        Write-WarningMessage "⚠️  No LLM API key configured (OPENAI_API_KEY or ANTHROPIC_API_KEY)"
    }
    else {
        Write-Host "✅ LLM API key configured"
    }

    if (-not $envValues.ContainsKey('TWOGIS_API_KEY') -or [string]::IsNullOrWhiteSpace($envValues['TWOGIS_API_KEY'])) {
        Write-WarningMessage "⚠️  TWOGIS_API_KEY not configured"
    }
    else {
        Write-Host "✅ 2GIS API key configured"
    }
}

Write-Host
Write-Info "📁 Checking project layout..."
$requiredPaths = @('proto', 'services', 'helm/ai-tourist', 'scripts')
foreach ($path in $requiredPaths) {
    if (Test-Path -LiteralPath $path) {
        Write-Host "✅ $path present"
    }
    else {
        Write-ErrorMessage "❌ $path missing"
        $ErrorCount += 1
    }
}

Write-Host
Write-Info "💾 Checking disk space..."
try {
    $currentPath = Get-Location
    $drive = Get-PSDrive -Name $currentPath.Drive.Name
    $freeGB = [math]::Round($drive.Free/1GB, 2)
    if ($freeGB -lt 20) {
        Write-WarningMessage "⚠️  Low disk space ($freeGB GB available). Recommended: 20GB+"
        Write-Host "   Free up space by:" -ForegroundColor DarkCyan
        Write-Host "     • Deleting old Minikube clusters: minikube delete" -ForegroundColor DarkCyan
        Write-Host "     • Cleaning Docker cache: docker system prune -af" -ForegroundColor DarkCyan
        Write-Host "     • Moving large downloads to an external drive" -ForegroundColor DarkCyan
    }
    else {
        Write-Host "✅ $freeGB GB available"
    }
}
catch {
    Write-WarningMessage "⚠️  Unable to determine disk space"
}

Write-Host
Write-Info "🛞 Minikube driver: $EffectiveDriver"
switch ($EffectiveDriver) {
    'docker' { Test-CommandInstalled -Command 'docker' -Label 'Docker' -Required $true -VersionScript { (docker --version) -replace ',.*','' } -HintTool 'docker' }
    'docker-containerd' { Test-CommandInstalled -Command 'docker' -Label 'Docker CLI' -Required $true -VersionScript { (docker --version) -replace ',.*','' } -HintTool 'docker' }
    'cri-dockerd' { Test-CommandInstalled -Command 'docker' -Label 'Docker CLI' -Required $true -VersionScript { (docker --version) -replace ',.*','' } -HintTool 'docker' }
    'podman' { Test-CommandInstalled -Command 'podman' -Label 'Podman' -Required $true -VersionScript { podman --version } -HintTool 'podman' }
    'virtualbox' { Test-CommandInstalled -Command 'VBoxManage' -Label 'VirtualBox' -Required $true -VersionScript { VBoxManage --version } -HintTool 'virtualbox' }
    'hyperkit' { Test-CommandInstalled -Command 'hyperkit' -Label 'HyperKit' -Required $true }
    'hyperv' { Write-Info "   Ensure the Hyper-V feature is enabled and a virtual switch is available." }
    default { Write-WarningMessage "⚠️  Unknown driver '$EffectiveDriver'. Verify the required hypervisor/runtime is installed." }
}
Write-Info "   Override driver: pwsh -File .\\scripts\\setup-check.ps1 -Driver <name>"

Write-Host
Write-Info "🧠 Checking hardware virtualization..."
try {
    $cpu = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1
    if ($null -ne $cpu -and $cpu.VirtualizationFirmwareEnabled) {
        Write-Host "✅ Firmware virtualization enabled"
    }
    else {
        Write-WarningMessage "⚠️  Firmware virtualization appears disabled. Enable Intel VT-x / AMD-V in BIOS/UEFI."
        Write-Host "   Steps:" -ForegroundColor DarkCyan
        Write-Host "     1. Reboot → tap F2/F10/Delete to open BIOS/UEFI" -ForegroundColor DarkCyan
        Write-Host "     2. Locate Virtualization/VT-x/SVM and set to Enabled" -ForegroundColor DarkCyan
        Write-Host "     3. Save changes, boot Windows, rerun this script" -ForegroundColor DarkCyan
    }

    if ($null -ne $cpu -and $cpu.SecondLevelAddressTranslationExtensions) {
        Write-Host "✅ SLAT (Second Level Address Translation) available"
    }
    else {
        Write-WarningMessage "⚠️  SLAT not reported. Hyper-V may be unavailable on this machine."
        Write-Host "   Workarounds:" -ForegroundColor DarkCyan
        Write-Host "     • Use the VirtualBox driver: -Driver virtualbox" -ForegroundColor DarkCyan
        Write-Host "     • Or enable WSL2 (requires Windows 10 2004+): wsl --install --no-distribution" -ForegroundColor DarkCyan
    }
}
catch {
    Write-WarningMessage "⚠️  Unable to query virtualization capabilities ($_)."
    Write-Host "   Run this PowerShell as Administrator and ensure the Hyper-V / Virtual Machine Platform features are enabled." -ForegroundColor DarkCyan
}

Write-Host
Write-Host "================================"
if ($ErrorCount -gt 0) {
    Write-ErrorMessage "❌ Setup check failed"
    Write-Host "Please resolve the errors above before deploying."
    exit 1
}
else {
    Write-Host "✅ Setup check passed" -ForegroundColor Green
    Write-Host "Next steps:"
    $driverHint = if ([string]::IsNullOrWhiteSpace($Driver)) { $EffectiveDriver } else { $Driver }
    Write-Host "  • ./scripts/judge-run.sh --driver=$driverHint" 
    Write-Host "    or"
    Write-Host "  • pwsh -File .\scripts\judge-run.ps1 -Driver $driverHint"
    Write-Host ""
    Write-Host "The judge-run helper script converts .env, starts Minikube, builds images, deploys the chart and runs smoke tests automatically."
}
