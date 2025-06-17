# PowerShell Script: setup-and-start.ps1

function Check-DockerCompose {
    if (-not (Get-Command "docker-compose" -ErrorAction SilentlyContinue) -and -not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
        Write-Host "Docker is not installed. Please install Docker Desktop and ensure 'docker compose' is available." -ForegroundColor Red
        exit 1
    }
}

function Prompt-EnvVar {
    param (
        [string]$VarName,
        [string]$DefaultValue,
        [switch]$OutputKeyPair
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

function Create-Directory-IfNotPresent {
    param ([string]$DirName)
    if (-not (Test-Path $DirName)) {
        New-Item -ItemType Directory -Path $DirName | Out-Null
        Write-Host "Created directory: $DirName"
    }
}

Write-Host "┌───────────────────────────────────────────────────┐"
Write-Host "│     Welcome to the Arthur GenAI Engine Setup!     │"
Write-Host "└───────────────────────────────────────────────────┘"

Check-DockerCompose

$userHome = [Environment]::GetFolderPath("UserProfile")
$rootDir = Join-Path $userHome ".arthur-engine\local-stack"
$genaiSubdir = Join-Path $rootDir "genai-engine"
$envFile = ".env"
$envPath = Join-Path $genaiSubdir $envFile

Create-Directory-IfNotPresent -DirName $genaiSubdir

if ((Test-Path $envPath) -and (Get-Item $envPath -ErrorAction SilentlyContinue).Length -gt 0) {
    Write-Host "The $envPath file already exists."
    Write-Host "Please review the file and press any key to proceed to Docker Compose up..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} else {
    Write-Host ""
    Write-Host "Do you have access to OpenAI services?"
    Write-Host ""
    Write-Host "Why we ask: Arthur uses your OpenAI key to run guardrails like hallucination and sensitive data checks—all within your environment, so your data never leaves your infrastructure."
    Write-Host "You can use a new or existing key tied to the OpenAI project/org your LLM calls are billed to."
    Write-Host "Don't have a key? You can skip for now and add it later. Just note: hallucination & sensitive data guardrails won't run without it."
    Write-Host ""
    $hasOpenAI = Read-Host "Do you have access to OpenAI? (y/n) [Default: y]"
    if ([string]::IsNullOrWhiteSpace($hasOpenAI)) {
        $hasOpenAI = "y"
    }

    if ($hasOpenAI -match "^[Yy]$") {
        Write-Host ""
        Write-Host "Enter the provider for OpenAI services (Format: Azure or OpenAI)"
        $provider = Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_PROVIDER" -DefaultValue "OpenAI" -OutputKeyPair
        Write-Host ""
        Write-Host "Enter the OpenAI GPT model name (Example: gpt-4o-mini-2024-07-18)"
        $model = Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_GPT_NAME" -DefaultValue "gpt-4o-mini-2024-07-18"
        Write-Host ""
        Write-Host "Enter the OpenAI GPT endpoint (Format: https://endpoint):"
        $endpoint = Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_GPT_ENDPOINT" -DefaultValue ""
        Write-Host ""
        Write-Host "Enter the OpenAI GPT API key:"
        $apiKey = Prompt-EnvVar -VarName "GENAI_ENGINE_OPENAI_GPT_API_KEY" -DefaultValue "changeme_api_key"

        $envContent = @"
$provider
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=$model::$endpoint::$apiKey
"@
        Set-Content -Path $envPath -Value $envContent -Encoding UTF8
    } else {
        Write-Host ""
        Write-Host "Skipping OpenAI configuration..."
        New-Item -ItemType File -Path $envPath -Force | Out-Null
    }
}

Write-Host ""
Write-Host "To see the $envFile file or docker-compose.yml, look in the $genaiSubdir directory."
Write-Host "We discourage moving this directory so you can continue using our automated workflow to update your configuration."
Write-Host ""
Write-Host "Downloading images (~2.24 GB) and running docker containers. This will take a few minutes..."
Write-Host ""

Start-Sleep -Seconds 1
Set-Location $genaiSubdir
try {
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/docker-compose/genai-engine/docker-compose.yml" -OutFile "docker-compose.yml"
} catch {
    Write-Host "Error downloading docker-compose.yml: $_"
    exit 1
}
docker compose up -d --pull always
