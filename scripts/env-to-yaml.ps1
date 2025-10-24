param(
    [string]$EnvPath = ".env",
    [string]$OutputPath = ".env.yaml",
    [string]$HelmSecretsPath = "helm/ai-tourist/secrets.yaml"
)

function Write-ErrorAndExit {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $EnvPath)) {
    Write-ErrorAndExit ".env file not found at $EnvPath"
}

$helmDir = Split-Path -LiteralPath $HelmSecretsPath -Parent
if (-not (Test-Path -LiteralPath $helmDir)) {
    Write-ErrorAndExit "Helm chart directory not found at $helmDir"
}

function Parse-EnvFile {
    param([string]$Path)
    $result = @{}
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

$envValues = Parse-EnvFile -Path $EnvPath

function Get-EnvValue {
    param(
        [string]$Key,
        [string]$Default = ''
    )
    if ($envValues.ContainsKey($Key) -and $envValues[$Key] -ne '') {
        return $envValues[$Key]
    }
    return $Default
}

$required = @('DB_PASSWORD', 'TWOGIS_API_KEY', 'JWT_SECRET_KEY', 'ENCRYPTION_KEY')
$missing = @()
foreach ($key in $required) {
    if (-not $envValues.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envValues[$key])) {
        $missing += $key
    }
}

if ($missing.Count -gt 0) {
    Write-ErrorAndExit "Missing required variables: $($missing -join ', ')"
}

if ([string]::IsNullOrWhiteSpace(Get-EnvValue -Key 'OPENAI_API_KEY') -and [string]::IsNullOrWhiteSpace(Get-EnvValue -Key 'ANTHROPIC_API_KEY')) {
    Write-Host "⚠️  No LLM API keys provided. The LLM service will use fallback responses." -ForegroundColor Yellow
}

function Validate-PositiveInteger {
    param([string]$Name, [string]$Value, [string]$Default)
    $effective = if ([string]::IsNullOrEmpty($Value)) { $Default } else { $Value }
    if ($effective -notmatch '^[0-9]+$') {
        Write-ErrorAndExit "$Name must be a positive integer (got '$Value')"
    }
    return $effective
}

function Normalize-Bool {
    param([string]$Name, [string]$Value, [string]$Default)
    $effective = if ([string]::IsNullOrEmpty($Value)) { $Default } else { $Value }
    $lower = $effective.ToLowerInvariant()
    if ($lower -in @('true', 'false')) { return $lower }
    Write-ErrorAndExit "$Name must be true or false (got '$Value')"
}

function Escape-Yaml {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    $escaped = $Value -replace '\\', '\\\\'
    $escaped = $escaped -replace '"', '\\"'
    return $escaped
}

$frontReplicas = Validate-PositiveInteger -Name 'FRONTEND_REPLICAS' -Value (Get-EnvValue -Key 'FRONTEND_REPLICAS') -Default '2'
$apiGatewayReplicas = Validate-PositiveInteger -Name 'API_GATEWAY_REPLICAS' -Value (Get-EnvValue -Key 'API_GATEWAY_REPLICAS') -Default '2'
$embeddingReplicas = Validate-PositiveInteger -Name 'EMBEDDING_REPLICAS' -Value (Get-EnvValue -Key 'EMBEDDING_REPLICAS') -Default '2'
$embeddingBatch = Validate-PositiveInteger -Name 'EMBEDDING_BATCH_SIZE' -Value (Get-EnvValue -Key 'EMBEDDING_BATCH_SIZE') -Default '32'
$rankingReplicas = Validate-PositiveInteger -Name 'RANKING_REPLICAS' -Value (Get-EnvValue -Key 'RANKING_REPLICAS') -Default '2'
$routePlannerReplicas = Validate-PositiveInteger -Name 'ROUTE_PLANNER_REPLICAS' -Value (Get-EnvValue -Key 'ROUTE_PLANNER_REPLICAS') -Default '2'
$llmReplicas = Validate-PositiveInteger -Name 'LLM_SERVICE_REPLICAS' -Value (Get-EnvValue -Key 'LLM_SERVICE_REPLICAS') -Default '1'
$geocodingReplicas = Validate-PositiveInteger -Name 'GEOCODING_REPLICAS' -Value (Get-EnvValue -Key 'GEOCODING_REPLICAS') -Default '1'
$poiReplicas = Validate-PositiveInteger -Name 'POI_REPLICAS' -Value (Get-EnvValue -Key 'POI_REPLICAS') -Default '1'

$postgresqlEnabled = Normalize-Bool -Name 'POSTGRESQL_ENABLED' -Value (Get-EnvValue -Key 'POSTGRESQL_ENABLED') -Default 'true'
$postgresqlPersistence = Normalize-Bool -Name 'POSTGRESQL_PERSISTENCE_ENABLED' -Value (Get-EnvValue -Key 'POSTGRESQL_PERSISTENCE_ENABLED') -Default 'true'
$redisEnabled = Normalize-Bool -Name 'REDIS_ENABLED' -Value (Get-EnvValue -Key 'REDIS_ENABLED') -Default 'true'
$redisPersistence = Normalize-Bool -Name 'REDIS_PERSISTENCE_ENABLED' -Value (Get-EnvValue -Key 'REDIS_PERSISTENCE_ENABLED') -Default 'true'
$ingressEnabled = Normalize-Bool -Name 'INGRESS_ENABLED' -Value (Get-EnvValue -Key 'INGRESS_ENABLED') -Default 'true'

$envYamlLines = @(
    "secrets:",
    "  dbPassword: \"$(Escape-Yaml (Get-EnvValue -Key 'DB_PASSWORD'))\"",
    "  openaiApiKey: \"$(Escape-Yaml (Get-EnvValue -Key 'OPENAI_API_KEY'))\"",
    "  anthropicApiKey: \"$(Escape-Yaml (Get-EnvValue -Key 'ANTHROPIC_API_KEY'))\"",
    "  twogisApiKey: \"$(Escape-Yaml (Get-EnvValue -Key 'TWOGIS_API_KEY'))\"",
    "  jwtSecret: \"$(Escape-Yaml (Get-EnvValue -Key 'JWT_SECRET_KEY'))\"",
    "  encryptionKey: \"$(Escape-Yaml (Get-EnvValue -Key 'ENCRYPTION_KEY'))\"",
    "",
    "frontend:",
    "  replicas: $frontReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'FRONTEND_IMAGE_TAG' -Default 'latest'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'FRONTEND_MEMORY_REQUEST' -Default '128Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'FRONTEND_CPU_REQUEST' -Default '100m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'FRONTEND_MEMORY_LIMIT' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'FRONTEND_CPU_LIMIT' -Default '200m'))\"",
    "",
    "apiGateway:",
    "  replicas: $apiGatewayReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'API_GATEWAY_IMAGE_TAG' -Default 'latest'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'API_GATEWAY_MEMORY_REQUEST' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'API_GATEWAY_CPU_REQUEST' -Default '200m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'API_GATEWAY_MEMORY_LIMIT' -Default '512Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'API_GATEWAY_CPU_LIMIT' -Default '500m'))\"",
    "",
    "embeddingService:",
    "  replicas: $embeddingReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'EMBEDDING_IMAGE_TAG' -Default 'latest'))\"",
    "  batchSize: $embeddingBatch",
    "  model: \"$(Escape-Yaml (Get-EnvValue -Key 'EMBEDDING_MODEL' -Default 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'EMBEDDING_MEMORY_REQUEST' -Default '512Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'EMBEDDING_CPU_REQUEST' -Default '500m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'EMBEDDING_MEMORY_LIMIT' -Default '1Gi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'EMBEDDING_CPU_LIMIT' -Default '1000m'))\"",
    "",
    "rankingService:",
    "  replicas: $rankingReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'RANKING_IMAGE_TAG' -Default 'latest'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'RANKING_MEMORY_REQUEST' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'RANKING_CPU_REQUEST' -Default '200m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'RANKING_MEMORY_LIMIT' -Default '512Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'RANKING_CPU_LIMIT' -Default '500m'))\"",
    "",
    "routePlannerService:",
    "  replicas: $routePlannerReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'ROUTE_PLANNER_IMAGE_TAG' -Default 'latest'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'ROUTE_PLANNER_MEMORY_REQUEST' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'ROUTE_PLANNER_CPU_REQUEST' -Default '200m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'ROUTE_PLANNER_MEMORY_LIMIT' -Default '512Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'ROUTE_PLANNER_CPU_LIMIT' -Default '500m'))\"",
    "",
    "llmService:",
    "  replicas: $llmReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'LLM_SERVICE_IMAGE_TAG' -Default 'latest'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'LLM_SERVICE_MEMORY_REQUEST' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'LLM_SERVICE_CPU_REQUEST' -Default '200m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'LLM_SERVICE_MEMORY_LIMIT' -Default '512Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'LLM_SERVICE_CPU_LIMIT' -Default '500m'))\"",
    "",
    "geocodingService:",
    "  replicas: $geocodingReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'GEOCODING_IMAGE_TAG' -Default 'latest'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'GEOCODING_MEMORY_REQUEST' -Default '128Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'GEOCODING_CPU_REQUEST' -Default '100m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'GEOCODING_MEMORY_LIMIT' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'GEOCODING_CPU_LIMIT' -Default '200m'))\"",
    "",
    "poiService:",
    "  replicas: $poiReplicas",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'POI_IMAGE_TAG' -Default 'latest'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'POI_MEMORY_REQUEST' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'POI_CPU_REQUEST' -Default '200m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'POI_MEMORY_LIMIT' -Default '512Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'POI_CPU_LIMIT' -Default '500m'))\"",
    "",
    "postgresql:",
    "  enabled: $postgresqlEnabled",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'POSTGRESQL_IMAGE_TAG' -Default '16-alpine'))\"",
    "  persistence:",
    "    enabled: $postgresqlPersistence",
    "    size: \"$(Escape-Yaml (Get-EnvValue -Key 'POSTGRESQL_STORAGE_SIZE' -Default '1Gi'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'POSTGRESQL_MEMORY_REQUEST' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'POSTGRESQL_CPU_REQUEST' -Default '250m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'POSTGRESQL_MEMORY_LIMIT' -Default '512Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'POSTGRESQL_CPU_LIMIT' -Default '500m'))\"",
    "",
    "redis:",
    "  enabled: $redisEnabled",
    "  image:",
    "    tag: \"$(Escape-Yaml (Get-EnvValue -Key 'REDIS_IMAGE_TAG' -Default '7-alpine'))\"",
    "  persistence:",
    "    enabled: $redisPersistence",
    "    size: \"$(Escape-Yaml (Get-EnvValue -Key 'REDIS_STORAGE_SIZE' -Default '1Gi'))\"",
    "  resources:",
    "    requests:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'REDIS_MEMORY_REQUEST' -Default '128Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'REDIS_CPU_REQUEST' -Default '100m'))\"",
    "    limits:",
    "      memory: \"$(Escape-Yaml (Get-EnvValue -Key 'REDIS_MEMORY_LIMIT' -Default '256Mi'))\"",
    "      cpu: \"$(Escape-Yaml (Get-EnvValue -Key 'REDIS_CPU_LIMIT' -Default '200m'))\"",
    "",
    "ingress:",
    "  enabled: $ingressEnabled",
    "  className: \"$(Escape-Yaml (Get-EnvValue -Key 'INGRESS_CLASS' -Default 'nginx'))\""
)

Set-Content -LiteralPath $OutputPath -Value $envYamlLines -Encoding UTF8

$secretsYamlLines = @(
    "secrets:",
    "  dbPassword: \"$(Escape-Yaml (Get-EnvValue -Key 'DB_PASSWORD'))\"",
    "  openaiApiKey: \"$(Escape-Yaml (Get-EnvValue -Key 'OPENAI_API_KEY'))\"",
    "  anthropicApiKey: \"$(Escape-Yaml (Get-EnvValue -Key 'ANTHROPIC_API_KEY'))\"",
    "  twogisApiKey: \"$(Escape-Yaml (Get-EnvValue -Key 'TWOGIS_API_KEY'))\"",
    "  jwtSecret: \"$(Escape-Yaml (Get-EnvValue -Key 'JWT_SECRET_KEY'))\"",
    "  encryptionKey: \"$(Escape-Yaml (Get-EnvValue -Key 'ENCRYPTION_KEY'))\""
)

Set-Content -LiteralPath $HelmSecretsPath -Value $secretsYamlLines -Encoding UTF8

Write-Host "✅ Generated $OutputPath and $HelmSecretsPath" -ForegroundColor Green
