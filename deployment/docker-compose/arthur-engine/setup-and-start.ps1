# PowerShell Script: setup-and-start.ps1

function Check-DockerCompose {
    if (-not (Get-Command "docker-compose" -ErrorAction SilentlyContinue) -and -not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
        Write-Host "Docker Compose is not installed. Please install Docker Desktop and try again." -ForegroundColor Red
        exit 1
    }
}

function Prompt-EnvVar {
    param (
        [string]$VarName,
        [string]$DefaultValue,
        [bool]$OutputKeyPair = $false
    )
    $inputValue = Read-Host "$VarName [Default: $DefaultValue]"
    if ([string]::IsNullOrWhiteSpace($inputValue)) {
        $inputValue = $DefaultValue
    }

    if ($OutputKeyPair) {
        return "$VarName=$inputValue"
    } else {
        return $inputValue
    }
}

function Parse-Boolean {
    param (
        [string]$FlagName,
        [string]$Value
    )
    $lower = $Value.ToLower()
    if ($lower -ne "true" -and $lower -ne "false") {
        Write-Host "$FlagName flag must be set to 'true' or 'false'." -ForegroundColor Red
        exit 1
    }
    return $lower
}

function Parse-ScriptVars {
    param(
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$Arguments
    )

    $allArgsString = $Arguments -join ' '

    $regex = '--[\w-]+=[^\s]+'
    $matches = [regex]::Matches($allArgsString, $regex)

    Write-Host "Found $($matches.Count) arguments."

    foreach ($match in $matches) {
        $arg = $match.Value
        if ($arg -match "^--arthur-api-host=(.+)") {
            [System.Environment]::SetEnvironmentVariable("ARTHUR_API_HOST", $Matches[1], "Process")
            Set-Variable -Name "ARTHUR_API_HOST" -Value $Matches[1] -Scope Script
        } elseif ($arg -match "^--arthur-client-id=(.+)") {
            [System.Environment]::SetEnvironmentVariable("ARTHUR_CLIENT_ID", $Matches[1], "Process")
            Set-Variable -Name "ARTHUR_CLIENT_ID" -Value $Matches[1] -Scope Script
        } elseif ($arg -match "^--arthur-client-secret=(.+)") {
            [System.Environment]::SetEnvironmentVariable("ARTHUR_CLIENT_SECRET", $Matches[1], "Process")
            Set-Variable -Name "ARTHUR_CLIENT_SECRET" -Value $Matches[1] -Scope Script
        } elseif ($arg -match "^--fetch-raw-data-enabled=(.+)") {
            $value = Parse-Boolean "--fetch-raw-data-enabled" $Matches[1]
            [System.Environment]::SetEnvironmentVariable("FETCH_RAW_DATA_ENABLED", $value, "Process")
            Set-Variable -Name "FETCH_RAW_DATA_ENABLED" -Value $value -Scope Script
        } elseif ($arg -match "^--default-genai-config=(.+)") {
            $value = Parse-Boolean "--default-genai-config" $Matches[1]
            [System.Environment]::SetEnvironmentVariable("DEFAULT_GENAI_CONFIG", $value, "Process")
            Set-Variable -Name "DEFAULT_GENAI_CONFIG" -Value $value -Scope Script
        } else {
            # This part of the logic might not be hit if the regex is good
            # but we keep it for safety.
            Write-Host "Unknown parameter: $arg"
            Write-Host "Usage: setup-and-start.ps1 --arthur-api-host=HOST --arthur-client-id=ID --arthur-client-secret=SECRET --fetch-raw-data-enabled=BOOL --default-genai-config=BOOL"
            # We don't exit here to allow other matched arguments to be processed.
        }
    }
}

function Create-DirectoryIfMissing {
    param ([string]$Dir)
    if (-not (Test-Path $Dir)) {
        New-Item -ItemType Directory -Path $Dir | Out-Null
        Write-Host "Created directory: $Dir"
    }
}

function Read-EnvFile {
    param ([string]$FilePath)
    if (Test-Path $FilePath) {
        Get-Content $FilePath | ForEach-Object {
            if ($_ -match "^\s*#") { return }
            if ($_ -match "^\s*$") { return }
            $parts = $_ -split "=", 2
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim('"')
                Set-Variable -Name $key -Value $value -Scope Script
            }
        }
    }
}

function Missing-MLEngineVars {
    $required = @("ARTHUR_CLIENT_ID", "ARTHUR_CLIENT_SECRET")
    $missing = @()
    foreach ($var in $required) {
        if ([string]::IsNullOrEmpty([System.Environment]::GetEnvironmentVariable($var, "Process"))) {
            $missing += $var
        }
    }
    if ($missing.Count -gt 0) {
        Write-Host "Missing required ML Engine variables:"
        $missing | ForEach-Object { Write-Host $_ }
        return $true
    }
    return $false
}

Write-Host "┌─────────────────────────────────────────────┐"
Write-Host "│     Welcome to the Arthur Engine Setup!     │"
Write-Host "└─────────────────────────────────────────────┘"

Check-DockerCompose

$userHome = [Environment]::GetFolderPath("UserProfile")
$rootDir = Join-Path $userHome ".arthur-engine\\local-stack"
$engineSubdir = Join-Path $rootDir "arthur-engine"
$envFilePath = Join-Path $engineSubdir ".env"

Create-DirectoryIfMissing -Dir $engineSubdir
Read-EnvFile -FilePath $envFilePath

# Split the arguments properly
$rawArgs = $MyInvocation.Line -replace '^.*\.ps1\s*', ''
$scriptArgs = $rawArgs -split '\s+(?=--)' | Where-Object { $_ -ne '' }
Parse-ScriptVars $scriptArgs

if (Missing-MLEngineVars) {
    Write-Host "Usage: setup-and-start.ps1 --arthur-api-host=HOST --arthur-client-id=ID --arthur-client-secret=SECRET --fetch-raw-data-enabled=BOOL --default-genai-config=BOOL"
    exit 1
}

$ARTHUR_API_HOST = if ($ARTHUR_API_HOST) { $ARTHUR_API_HOST } else { "https://platform.arthur.ai" }
$FETCH_RAW_DATA_ENABLED = if ($FETCH_RAW_DATA_ENABLED) { $FETCH_RAW_DATA_ENABLED } else { "true" }
$DEFAULT_GENAI_CONFIG = if ($DEFAULT_GENAI_CONFIG) { $DEFAULT_GENAI_CONFIG } else { "false" }

$envLines = @(
    "########################################################"
    "## Arthur ML Engine Environment Variables"
    "########################################################"
    "ARTHUR_API_HOST=$ARTHUR_API_HOST"
    "ARTHUR_CLIENT_ID=$ARTHUR_CLIENT_ID"
    "ARTHUR_CLIENT_SECRET=$ARTHUR_CLIENT_SECRET"
    "FETCH_RAW_DATA_ENABLED=$FETCH_RAW_DATA_ENABLED"
    ""
    "########################################################"
    "## Arthur Gen AI Engine Environment Variables"
    "########################################################"
)

if ($DEFAULT_GENAI_CONFIG -eq "true") {
    Write-Host "Skipping OpenAI configuration as --default-genai-config is set..."
    if ($GENAI_ENGINE_OPENAI_PROVIDER) {
        $envLines += "GENAI_ENGINE_OPENAI_PROVIDER=$GENAI_ENGINE_OPENAI_PROVIDER"
    }
    if ($GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS) {
        $envLines += "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS"
    }
} else {
    if (-not $GENAI_ENGINE_OPENAI_PROVIDER) {
        $openai = Read-Host "Do you have access to OpenAI? (y/n) [Default: y]"
        $openai = if ([string]::IsNullOrWhiteSpace($openai)) { "y" } else { $openai }

        if ($openai -match "^[Yy]$") {
            $envLines += Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_PROVIDER" -DefaultValue "OpenAI" -OutputKeyPair $true
            $gptName = Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_GPT_NAME" -DefaultValue "gpt-4o-mini-2024-07-18"
            $gptEndpoint = Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_GPT_ENDPOINT" -DefaultValue ""
            $gptKey = Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_GPT_API_KEY" -DefaultValue "changeme_api_key"
            $envLines += "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$gptName::$gptEndpoint::$gptKey"
        } else {
            Write-Host "Skipping OpenAI configuration..."
        }
    } else {
        Write-Host "Using existing OpenAI configuration from .env..."
        $envLines += "GENAI_ENGINE_OPENAI_PROVIDER=$GENAI_ENGINE_OPENAI_PROVIDER"
        $envLines += "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS"
    }
}

# Prompt for secret store key if not already set
if (-not $GENAI_ENGINE_SECRET_STORE_KEY) {
    Write-Host ""
    Write-Host "Enter the secret store encryption key for securing sensitive data:"
    Write-Host "This key is used to encrypt/decrypt secrets stored in the database."
    Write-Host "Keep this key secure and consistent across deployments."
    $secretKey = Prompt-EnvVar -VarName "GENAI_ENGINE_SECRET_STORE_KEY" -DefaultValue "changeme_secret_key"
    $envLines += "GENAI_ENGINE_SECRET_STORE_KEY=$secretKey"
} else {
    Write-Host ""
    Write-Host "Using existing GENAI_ENGINE_SECRET_STORE_KEY from config file..."
    $envLines += "GENAI_ENGINE_SECRET_STORE_KEY=$GENAI_ENGINE_SECRET_STORE_KEY"
}

$envLines | Set-Content -Path $envFilePath

Write-Host ""
Write-Host "Updated .env file at $envFilePath"
Write-Host "To see the .env file or docker-compose.yml, look in the $engineSubdir directory."
Write-Host "We discourage moving this directory so you can continue using our automated workflow to update your configuration."
Write-Host "Downloading images (~2.86 GB) and running docker containers. This will take a few minutes..."

Start-Sleep -Seconds 1
Set-Location -Path $engineSubdir
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/arthur-engine/docker-compose.yml" -OutFile "docker-compose.yml"
docker compose up -d --pull always
