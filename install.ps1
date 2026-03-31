#!/usr/bin/env pwsh

<#
.SYNOPSIS
    diaMCP installer for Windows (requires WSL2)
.DESCRIPTION
    Installs or updates diaMCP on Windows systems. Requires Docker Desktop
    and WSL2 to be installed first.
.NOTES
    Run this in PowerShell as Administrator if needed:
    irm https://raw.githubusercontent.com/chartrambiz/diaMCP/main/install.ps1 | iex
#>

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/chartrambiz/diaMCP.git"
$INSTALL_DIR = "$HOME/diaMCP"

function Write-Step {
    param([string]$Message)
    Write-Host "`n>>> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."

    # Check if running in WSL
    if (-not (Test-Path "/proc/version") -or -not (Select-String -InputObject (Get-Content "/proc/version" -Raw) -Pattern "WSL")) {
        Write-Err "This script must be run inside WSL2 (Windows Subsystem for Linux)."
        Write-Host "Please open Ubuntu (or your WSL distro) and run:"
        Write-Host "    curl -fsSL https://raw.githubusercontent.com/chartrambiz/diaMCP/main/install.sh | sh" -ForegroundColor Yellow
        Write-Host "`nOr in WSL bash:"
        Write-Host "    bash -c '$(Get-Content "$PSScriptRoot\install.sh" -Raw | Out-String)'" -ForegroundColor Yellow
        exit 1
    }

    # Check Docker in WSL
    Write-Host "  Checking Docker in WSL..."
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Err "Docker is not installed in WSL."
        Write-Host "Please install Docker Desktop for Windows with WSL2 backend."
        exit 1
    }

    # Check Docker Compose in WSL
    Write-Host "  Checking Docker Compose in WSL..."
    if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Host "  Docker Compose not found, checking if 'docker compose' plugin is available..."
        if (-not (Get-Command "docker" -ErrorAction SilentlyContinue | Select-String -InputObject {(Get-Command $_).Source} -Pattern "docker")) {
            Write-Warn "Docker Compose may not be available."
        }
    }

    Write-Success "Prerequisites check passed"
}

function Install-DiaMCP {
    Write-Step "Installing diaMCP..."

    # Clone or update repo
    if (Test-Path "$INSTALL_DIR") {
        Write-Host "  Repository exists, pulling latest..."
        Set-Location "$INSTALL_DIR"
        bash -c "git pull origin main 2>/dev/null || git pull origin master"
    } else {
        Write-Host "  Cloning repository..."
        git clone $REPO_URL "$INSTALL_DIR"
        Set-Location "$INSTALL_DIR"
    }

    Write-Host "  Building Docker container..."
    docker compose build

    Write-Host "  Starting container..."
    docker compose up -d

    Write-Success "diaMCP is now running!"
}

function Show-NextSteps {
    Write-Step "Next Steps"
    Write-Host @"

1. Make sure llama-server is running with MCP support:
   llama-server --webui-mcp-proxy -m model.gguf -c 32768 --host 0.0.0.0 --port 8080

2. Open the llama.cpp webui in your browser

3. In the webui:
   - Go to MCP Settings
   - Toggle "Enable llama-server proxy" ON
   - Add the MCP URL: http://localhost:8000/mcp

4. The MCP tools will be available in your chat!

To update diaMCP later, run:
    cd ~/diaMCP && docker compose up --build -d

To view logs:
    cd ~/diaMCP && docker compose logs -f

To stop diaMCP:
    cd ~/diaMCP && docker compose down
"@
}

# Main
Write-Host "`n=== diaMCP Windows Installer ===" -ForegroundColor Magenta
Write-Host "This script must be run inside WSL2!" -ForegroundColor Yellow
Write-Host ""

Test-Prerequisites
Install-DiaMCP
Show-NextSteps
