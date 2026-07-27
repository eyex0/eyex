#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start a complete local πX development environment.

.DESCRIPTION
    Requires Docker and Docker Compose for Postgres/Redis.
    Starts the database services, runs migrations, seeds demo data, then starts
    the Python backend and Vite frontend in background processes.

.USAGE
    .\scripts\start-local.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "pix-backend"
$FrontendDir = $Root
$PidFile = Join-Path $Root ".local-pids"

function Test-Command($Name) {
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Wait-Postgres {
    param([string]$Container = "pix-postgres")
    Write-Host "Waiting for Postgres container '$Container' to be ready..."
    $attempts = 0
    while ($attempts -lt 60) {
        $ready = & docker exec $Container pg_isready -U pix 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Postgres is ready."
            return
        }
        Start-Sleep -Seconds 1
        $attempts++
    }
    throw "Postgres did not become ready within 60 seconds."
}

# --- Preconditions ---
Write-Host "==> πX local dev start"

if (-not (Test-Path (Join-Path $BackendDir ".env"))) {
    throw "Backend .env not found. Copy pix-backend/.env.example to pix-backend/.env and fill in real values."
}

if (-not (Test-Command "docker")) {
    throw "Docker is not installed or not in PATH. Install Docker Desktop first: https://www.docker.com/products/docker-desktop"
}

if (-not (Test-Command "npm")) {
    throw "npm is not installed or not in PATH. Install Node.js first."
}

if (-not (Test-Command "python")) {
    throw "python is not installed or not in PATH."
}

# --- Start infrastructure ---
Write-Host "==> Starting Postgres and Redis via Docker Compose"
Push-Location $Root
& docker compose -f docker-compose.yml up -d postgres redis
if ($LASTEXITCODE -ne 0) { throw "Failed to start Docker Compose services" }
Pop-Location

Wait-Postgres

# --- Migrations ---
Write-Host "==> Running database migrations"
Push-Location $BackendDir
& python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Migrations failed" }
Pop-Location

# --- Seed demo data ---
Write-Host "==> Seeding demo data"
Push-Location $BackendDir
& python scripts/seed_demo.py
if ($LASTEXITCODE -ne 0) { throw "Seeding failed" }
Pop-Location

# --- Start backend ---
Write-Host "==> Starting backend on http://localhost:8000"
$backend = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" `
    -WorkingDirectory $BackendDir `
    -PassThru -WindowStyle Hidden

# --- Start frontend ---
Write-Host "==> Starting frontend dev server"
$frontend = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $FrontendDir `
    -PassThru -WindowStyle Hidden

# --- Record PIDs for cleanup ---
@(
    "backend=$($backend.Id)"
    "frontend=$($frontend.Id)"
) | Set-Content -Path $PidFile

# --- Wait for services ---
Write-Host "==> Waiting for services to come up"
$backendReady = $false
$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (-not $backendReady) {
        try {
            $resp = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 2
            if ($resp.status -eq "ok" -or $resp.status -eq "healthy") {
                $backendReady = $true
            }
        } catch {
            # ignore
        }
    }
    if (-not $frontendReady) {
        try {
            $tcp = Test-NetConnection -ComputerName localhost -Port 3000 -WarningAction SilentlyContinue
            if ($tcp.TcpTestSucceeded) {
                $frontendReady = $true
            }
        } catch {
            # ignore
        }
    }
    if ($backendReady -and $frontendReady) { break }
}

if (-not $backendReady) {
    Write-Warning "Backend health check did not succeed. Check logs: Get-Content $BackendDir/..."
}
if (-not $frontendReady) {
    Write-Warning "Frontend dev server did not open port 3000. Check the frontend log above."
}

Write-Host ""
Write-Host "πX local environment is starting."
Write-Host "  Backend:   http://localhost:8000"
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  Health:    http://localhost:8000/health"
Write-Host ""
Write-Host "To stop background processes:"
Write-Host "  Get-Content '$PidFile'"
Write-Host "  Stop-Process -Id <id>"
Write-Host "  docker compose -f docker-compose.yml down"
