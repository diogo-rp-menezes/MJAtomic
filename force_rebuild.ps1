# force_rebuild.ps1
# Script para forçar a reconstrução limpa do ambiente Docker e resolver cache "stale"

# Usar "Continue" para que o script não pare se uma imagem não existir para ser removida.
$ErrorActionPreference = "Continue"

# Função para carregar variáveis de um arquivo .env para a sessão atual
function Load-DotEnv {
    param ([string]$Path = ".env.local")
    if (-not (Test-Path $Path)) {
        Write-Host "AVISO: Arquivo '$Path' não encontrado. Usando variáveis de ambiente existentes." -ForegroundColor Yellow
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and $line -notmatch "^\s*#") {
            $parts = $line -split "=", 2
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                # Remove aspas do valor, se houver
                $value = $value -replace '^"|"$' -replace "^'|'$"
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Write-Host "Variáveis de '$Path' carregadas no ambiente." -ForegroundColor Gray
}

Write-Host "---------------------------------------------------" -ForegroundColor Cyan
Write-Host "       DevAgent Atomic - Force Rebuild             " -ForegroundColor Cyan
Write-Host "---------------------------------------------------" -ForegroundColor Cyan

# 0. Carregar variáveis de ambiente
Write-Host "[0/4] Carregando variáveis de .env.local..." -ForegroundColor Yellow
Load-DotEnv

# 1. Parar e Remover Contêineres
Write-Host "[1/4] Derrubando contêineres existentes..." -ForegroundColor Yellow
docker compose -f infra/docker-compose.yml down

# 2. Remover a Imagem Antiga
Write-Host "[2/4] Removendo imagem antiga da API..." -ForegroundColor Yellow
docker image rm mjatomic-api -f
docker image rm dev-agent-atomic-api -f

# 3. Construir e Iniciar do Zero
Write-Host "[3/4] Construindo e iniciando do zero (Force Build)..." -ForegroundColor Yellow
docker compose -f infra/docker-compose.yml up --build -d

# 4. Conclusão
Write-Host "---------------------------------------------------" -ForegroundColor Green
Write-Host "[4/4] Processo concluído! O ambiente foi recriado." -ForegroundColor Green
Write-Host "Verifique o dashboard em: http://localhost:8001/dashboard" -ForegroundColor White
Write-Host "---------------------------------------------------" -ForegroundColor Green
