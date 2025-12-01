# force_rebuild.ps1
# Script para forçar a reconstrução limpa do ambiente Docker e resolver cache "stale"

$ErrorActionPreference = "Continue"

Write-Host "---------------------------------------------------" -ForegroundColor Cyan
Write-Host "       DevAgent Atomic - Force Rebuild             " -ForegroundColor Cyan
Write-Host "---------------------------------------------------" -ForegroundColor Cyan

# 1. Parar e Remover Contêineres
Write-Host "[1/3] Derrubando contêineres existentes..." -ForegroundColor Yellow
docker compose -f infra/docker-compose.yml down

# 2. Remover a Imagem Antiga
Write-Host "[2/3] Removendo imagem antiga da API..." -ForegroundColor Yellow
# Remove a imagem específica relatada (mjatomic-api) e também tenta variações comuns
# O erro é suprimido caso a imagem não exista
docker image rm mjatomic-api -f 2>$null
docker image rm dev-agent-atomic-api -f 2>$null

# 3. Construir e Iniciar do Zero
Write-Host "[3/3] Construindo e iniciando do zero (Force Build)..." -ForegroundColor Yellow
docker compose -f infra/docker-compose.yml up --build -d

Write-Host "---------------------------------------------------" -ForegroundColor Green
Write-Host "Processo concluído! O ambiente foi recriado." -ForegroundColor Green
Write-Host "Verifique o dashboard em: http://localhost:8001/dashboard" -ForegroundColor White
Write-Host "---------------------------------------------------" -ForegroundColor Green
