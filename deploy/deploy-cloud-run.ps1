param(
    [string]$ProjectId = "",
    [string]$Region = "us-central1",
    [string]$Repository = "langgraph-text-to-sql",
    [string]$ImageName = "langgraph-text-to-sql-streamlit",
    [string]$ServiceName = "langgraph-text-to-sql",
    [string]$ServiceAccountName = "cr-langgraph-text-to-sql",
    [switch]$AllowUnauthenticated = $true
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$EnvPath = Join-Path $RepoRoot ".env"

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path $Path)) {
        throw "No existe el archivo .env en $Path"
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }

        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $values[$key] = $value
    }

    return $values
}

function Require-EnvValue {
    param(
        [hashtable]$Values,
        [string]$Name
    )

    if (-not $Values.ContainsKey($Name) -or [string]::IsNullOrWhiteSpace($Values[$Name])) {
        throw "Falta $Name en .env"
    }

    return $Values[$Name]
}

function Invoke-Gcloud {
    param([string[]]$GcloudArgs)

    Write-Host "gcloud $($GcloudArgs -join ' ')" -ForegroundColor DarkGray
    & gcloud @GcloudArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el comando: gcloud $($GcloudArgs -join ' ')"
    }
}

function Test-GcloudCommand {
    param([string[]]$GcloudArgs)

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & gcloud @GcloudArgs *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Ensure-Secret {
    param(
        [string]$Name,
        [string]$Value,
        [string]$ProjectId,
        [string]$ServiceAccountEmail
    )

    if (-not (Test-GcloudCommand @("secrets", "describe", $Name, "--project", $ProjectId))) {
        Invoke-Gcloud @("secrets", "create", $Name, "--replication-policy=automatic", "--project", $ProjectId)
    }

    Write-Host "Subiendo nueva version del secreto $Name" -ForegroundColor Cyan
    $tempSecretFile = New-TemporaryFile
    try {
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($tempSecretFile.FullName, $Value, $utf8NoBom)

        Invoke-Gcloud @(
            "secrets", "versions", "add", $Name,
            "--data-file", $tempSecretFile.FullName,
            "--project", $ProjectId
        )
    }
    finally {
        Remove-Item -LiteralPath $tempSecretFile.FullName -Force -ErrorAction SilentlyContinue
    }

    Invoke-Gcloud @(
        "secrets", "add-iam-policy-binding", $Name,
        "--member", "serviceAccount:$ServiceAccountEmail",
        "--role", "roles/secretmanager.secretAccessor",
        "--project", $ProjectId
    )
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    throw "gcloud no esta instalado o no esta en el PATH. Instala Google Cloud CLI y ejecuta: gcloud init"
}

$envValues = Read-DotEnv $EnvPath

if (-not $ProjectId) {
    $ProjectId = Require-EnvValue $envValues "GOOGLE_CLOUD_PROJECT"
}

$OpenAiApiKey = Require-EnvValue $envValues "OPENAI_API_KEY"
$DbUser = Require-EnvValue $envValues "DB_USER"
$DbPassword = Require-EnvValue $envValues "DB_PASSWORD"
$DbHost = Require-EnvValue $envValues "DB_HOST"
$DbPort = if ($envValues.ContainsKey("DB_PORT")) { $envValues["DB_PORT"] } else { "5432" }
$DbName = if ($envValues.ContainsKey("DB_NAME")) { $envValues["DB_NAME"] } else { "postgres" }
$DbSchema = if ($envValues.ContainsKey("DB_SCHEMA")) { $envValues["DB_SCHEMA"] } else { "public" }
$GcpLocation = if ($envValues.ContainsKey("GOOGLE_CLOUD_LOCATION")) { $envValues["GOOGLE_CLOUD_LOCATION"] } else { $Region }

$ServiceAccountEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"
$ImageUri = "$Region-docker.pkg.dev/$ProjectId/$Repository/${ImageName}:latest"

Write-Host "Proyecto: $ProjectId" -ForegroundColor Green
Write-Host "Region: $Region" -ForegroundColor Green
Write-Host "Servicio Cloud Run: $ServiceName" -ForegroundColor Green
Write-Host "Imagen: $ImageUri" -ForegroundColor Green

Invoke-Gcloud @("config", "set", "project", $ProjectId)

Invoke-Gcloud @(
    "services", "enable",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "bigquery.googleapis.com",
    "bigquerystorage.googleapis.com",
    "--project", $ProjectId
)

if (-not (Test-GcloudCommand @("artifacts", "repositories", "describe", $Repository, "--location", $Region, "--project", $ProjectId))) {
    Invoke-Gcloud @(
        "artifacts", "repositories", "create", $Repository,
        "--repository-format", "docker",
        "--location", $Region,
        "--description", "Imagenes Docker del agente LangGraph Text-to-SQL",
        "--project", $ProjectId
    )
}

if (-not (Test-GcloudCommand @("iam", "service-accounts", "describe", $ServiceAccountEmail, "--project", $ProjectId))) {
    Invoke-Gcloud @(
        "iam", "service-accounts", "create", $ServiceAccountName,
        "--display-name", "Cloud Run LangGraph Text-to-SQL",
        "--project", $ProjectId
    )
}

Invoke-Gcloud @(
    "projects", "add-iam-policy-binding", $ProjectId,
    "--member", "serviceAccount:$ServiceAccountEmail",
    "--role", "roles/bigquery.jobUser"
)

Invoke-Gcloud @(
    "projects", "add-iam-policy-binding", $ProjectId,
    "--member", "serviceAccount:$ServiceAccountEmail",
    "--role", "roles/bigquery.readSessionUser"
)

Ensure-Secret -Name "openai-api-key" -Value $OpenAiApiKey -ProjectId $ProjectId -ServiceAccountEmail $ServiceAccountEmail
Ensure-Secret -Name "supabase-db-password" -Value $DbPassword -ProjectId $ProjectId -ServiceAccountEmail $ServiceAccountEmail

Push-Location $RepoRoot
try {
    Invoke-Gcloud @(
        "builds", "submit", ".",
        "--config", "deploy/cloudbuild.yaml",
        "--substitutions", "_REGION=$Region,_AR_REPO=$Repository,_IMAGE_NAME=$ImageName",
        "--project", $ProjectId
    )
}
finally {
    Pop-Location
}

$envVars = @(
    "GOOGLE_CLOUD_PROJECT=$ProjectId",
    "GOOGLE_CLOUD_LOCATION=$GcpLocation",
    "DB_USER=$DbUser",
    "DB_HOST=$DbHost",
    "DB_PORT=$DbPort",
    "DB_NAME=$DbName",
    "DB_SCHEMA=$DbSchema"
) -join ","

$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--image", $ImageUri,
    "--region", $Region,
    "--platform", "managed",
    "--service-account", $ServiceAccountEmail,
    "--set-env-vars", $envVars,
    "--update-secrets", "OPENAI_API_KEY=openai-api-key:latest,DB_PASSWORD=supabase-db-password:latest",
    "--memory", "1Gi",
    "--cpu", "1",
    "--timeout", "900",
    "--concurrency", "10",
    "--project", $ProjectId
)

if ($AllowUnauthenticated) {
    $deployArgs += "--allow-unauthenticated"
}
else {
    $deployArgs += "--no-allow-unauthenticated"
}

Invoke-Gcloud $deployArgs

Write-Host "Deploy terminado." -ForegroundColor Green
Invoke-Gcloud @("run", "services", "describe", $ServiceName, "--region", $Region, "--project", $ProjectId, "--format", "value(status.url)")
