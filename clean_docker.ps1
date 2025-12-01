# clean_docker.ps1
# Script para realizar uma limpeza completa do ambiente Docker, removendo
# contêineres, redes, volumes e imagens não utilizados.

$ErrorActionPreference = "Continue"

Write-Host "---------------------------------------------------" -ForegroundColor Magenta
Write-Host "       Limpeza Profunda do Ambiente Docker         " -ForegroundColor Magenta
Write-Host "---------------------------------------------------" -ForegroundColor Magenta
Write-Host "AVISO: Este script irá parar e remover TODOS os contêineres Docker em execução." -ForegroundColor Yellow

# Pausa para confirmação do usuário
Read-Host -Prompt "Pressione Enter para continuar ou CTRL+C para cancelar"

# 1. Parar TODOS os contêineres em execução
Write-Host "[1/4] Parando todos os contêineres Docker..." -ForegroundColor Cyan
docker stop $(docker ps -q)

# 2. Remover TODOS os contêineres (parados e em execução)
Write-Host "[2/4] Removendo todos os contêineres..." -ForegroundColor Cyan
docker rm $(docker ps -a -q)

# 3. Remover redes não utilizadas (órfãs)
Write-Host "[3/4] Removendo redes Docker não utilizadas..." -ForegroundColor Cyan
docker network prune -f

# 4. Limpeza geral do sistema Docker (Prune)
Write-Host "[4/4] Executando limpeza geral do sistema (imagens, cache de build, etc.)..." -ForegroundColor Cyan
# O comando 'docker system prune' remove:
# - Todos os contêineres parados
# - Todas as redes não utilizadas
# - Todas as imagens "dangling" (sem tag)
# - Todo o cache de build
docker system prune -a -f --volumes

Write-Host "---------------------------------------------------" -ForegroundColor Green
Write-Host "Limpeza concluída com sucesso!" -ForegroundColor Green
Write-Host "Seu ambiente Docker está limpo." -ForegroundColor Green
Write-Host "Execute './start_local.ps1 -Clean' para construir o projeto do zero." -ForegroundColor White
Write-Host "---------------------------------------------------" -ForegroundColor Green
