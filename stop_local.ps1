# stop_local.ps1
# Para todos os serviços do ambiente de desenvolvimento local.

Write-Host "Parando todos os serviços do MJAtomic..." -ForegroundColor Yellow
docker compose -f infra/docker-compose.yml down
Write-Host "Serviços parados." -ForegroundColor Green
