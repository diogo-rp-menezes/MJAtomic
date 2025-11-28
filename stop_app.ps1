# stop_app.ps1
Write-Host "Parando containers do Docker..." -ForegroundColor Yellow
docker-compose -f infra/docker-compose.yml stop
Write-Host "Sistema pausado." -ForegroundColor Green