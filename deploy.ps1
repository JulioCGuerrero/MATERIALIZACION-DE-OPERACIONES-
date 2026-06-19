param(
    [string]$ProjectId = "desplieguecrmquejas",
    [string]$ServiceName = "materializacion-operaciones",
    [string]$Region = "us-central1",
    [string]$ImageName = "",
    [string]$SqlProjectId = "trusty-agility-439318-a8",
    [string]$InstanceConnectionName = "trusty-agility-439318-a8:northamerica-south1:materializacion",
    [string]$BucketName = "materializacion-operaciones-documentos-1066651007132",
    [string]$ServiceAccount = "1066651007132-compute@developer.gserviceaccount.com",
    [string]$DatabaseSecret = "materializacion-database-url",
    [string]$AppSecret = "materializacion-secret-key",
    [switch]$RequireAuthentication
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "No se encontró gcloud en PATH."
}
if ([string]::IsNullOrWhiteSpace($ImageName)) {
    $ImageName = "gcr.io/$ProjectId/$ServiceName"
}

$requiredSecrets = @($DatabaseSecret, $AppSecret) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
foreach ($secret in $requiredSecrets) {
    & gcloud secrets describe $secret --project $ProjectId --quiet 1>$null
    if ($LASTEXITCODE -ne 0) { throw "Falta el secreto requerido: $secret" }
}

& gcloud sql instances describe materializacion --project $SqlProjectId --quiet 1>$null
if ($LASTEXITCODE -ne 0) { throw "No se encontro la instancia Cloud SQL materializacion en $SqlProjectId." }

& gcloud storage buckets describe "gs://$BucketName" --project $ProjectId --quiet 1>$null
if ($LASTEXITCODE -ne 0) { throw "No se encontro el bucket requerido: gs://$BucketName" }

Write-Host "Construyendo $ImageName"
& gcloud builds submit --project $ProjectId --tag $ImageName .
if ($LASTEXITCODE -ne 0) { throw "Falló la construcción de la imagen." }

$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--project", $ProjectId,
    "--region", $Region,
    "--image", $ImageName,
    "--platform", "managed",
    "--port", "8080",
    "--memory", "1Gi",
    "--cpu", "1",
    "--concurrency", "40",
    "--min", "0",
    "--max", "3",
    "--timeout", "300",
    "--quiet"
)
$envVars = @(
    "MAX_UPLOAD_MB=25",
    "AUTO_CREATE_SCHEMA=false",
    "INSTANCE_CONNECTION_NAME=$InstanceConnectionName"
)
if (-not [string]::IsNullOrWhiteSpace($BucketName)) { $envVars += "STORAGE_BUCKET=$BucketName" }
$deployArgs += @("--set-env-vars", ($envVars -join ","))
if (-not [string]::IsNullOrWhiteSpace($ServiceAccount)) { $deployArgs += @("--service-account", $ServiceAccount) }
if (-not [string]::IsNullOrWhiteSpace($InstanceConnectionName)) { $deployArgs += @("--add-cloudsql-instances", $InstanceConnectionName) }
$secretVars = @()
if (-not [string]::IsNullOrWhiteSpace($DatabaseSecret)) { $secretVars += "DATABASE_URL=$DatabaseSecret`:latest" }
if (-not [string]::IsNullOrWhiteSpace($AppSecret)) { $secretVars += "SECRET_KEY=$AppSecret`:latest" }
if ($secretVars.Count -gt 0) { $deployArgs += @("--set-secrets", ($secretVars -join ",")) }
$deployArgs += if ($RequireAuthentication) { "--no-allow-unauthenticated" } else { "--allow-unauthenticated" }

Write-Host "Desplegando $ServiceName"
& gcloud @deployArgs
if ($LASTEXITCODE -ne 0) { throw "Falló el despliegue de Cloud Run." }

$serviceUrl = (& gcloud run services describe $ServiceName --project $ProjectId --region $Region --format="value(status.url)").Trim()
$health = Invoke-RestMethod -Uri "$serviceUrl/api/health" -TimeoutSec 30
if ($health.status -ne "ok") { throw "El health check no respondió correctamente." }
Write-Host "Deploy terminado y validado: $serviceUrl"
