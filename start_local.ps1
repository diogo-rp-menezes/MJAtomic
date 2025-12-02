# start_local.ps1
# Ponto de entrada principal para iniciar o ambiente de desenvolvimento local.

param (
    [switch]$Clean = $false
)

# Usar "Continue" para que o script não pare em erros não-críticos (ex: imagem não existe)
$ErrorActionPreference = "Continue"

# Função para carregar variáveis de .env.local
function Load-DotEnv {
    $envPath = ".env.local"
    if (-not (Test-Path $envPath)) {
        Write-Host "AVISO: '$envPath' não encontrado. Copiando de .env.example." -ForegroundColor Yellow
        Copy-Item ".env.example" $envPath
    }
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and $line -notmatch "^\s*#") {
            $parts = $line -split "=", 2
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim() -replace '^"|"$' -replace "^'|'$"
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Write-Host "Variáveis de '$envPath' carregadas." -ForegroundColor Gray
}

# --- Início da Execução ---
Write-Host "---------------------------------------------------" -ForegroundColor Cyan
Write-Host "       Iniciando Ambiente Local - MJAtomic         " -ForegroundColor Cyan
Write-Host "---------------------------------------------------"

# 1. Carregar .env.local
Load-DotEnv

# 2. Limpeza (se a flag -Clean for usada)
if ($Clean) {
    Write-Host "[1/4] MODO LIMPO: Derrubando contêineres e volumes..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml down -v # O -v remove os volumes, incluindo o do banco de dados
    Write-Host "[2/4] Removendo imagens antigas..." -ForegroundColor Yellow
    docker image rm mjatomic-api -f
    docker image rm dev-agent-atomic-api -f
} else {
    Write-Host "[1/4] Derrubando contêineres (se existentes)..." -ForegroundColor Gray
    docker compose -f infra/docker-compose.yml down
}

# 3. Subir a infraestrutura (DB e Redis) PRIMEIRO e esperar
Write-Host "[2/4] Iniciando infraestrutura (DB, Redis) e aguardando prontidão..." -ForegroundColor Cyan
docker compose -f infra/docker-compose.yml up -d db redis

# Loop para esperar o PostgreSQL ficar pronto
$max_retries = 20
$retry_count = 0
$db_ready = $false

Write-Host "Aguardando conexão com o banco de dados..." -NoNewline
do {
    try {
        $logs = docker logs devagent_db 2>&1
        if ($logs -match "database system is ready to accept connections") {
            $db_ready = $true
            Write-Host "" # Nova linha para formatação
            Write-Host "Banco de dados está pronto!" -ForegroundColor Green
        } else {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds 3
            $retry_count++
        }
    } catch {
        Write-Host "x" -NoNewline
        Start-Sleep -Seconds 3
        $retry_count++
    }
} while (-not $db_ready -and $retry_count -lt $max_retries)

if (-not $db_ready) {
    Write-Host "" # Nova linha para formatação
    Write-Host "ERRO: Banco de dados não iniciou a tempo. Verifique os logs do contêiner 'devagent_db'." -ForegroundColor Red
    exit 1
}

# 4. Subir o restante dos serviços
Write-Host "[3/4] Iniciando os serviços restantes (API, Worker)..." -ForegroundColor Cyan
docker compose -f infra/docker-compose.yml up --build -d api worker

# 5. Conclusão
Write-Host "[4/4] Processo concluído! O ambiente está online." -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8001/dashboard" -ForegroundColor White
Write-Host "Para ver os logs: docker compose -f infra/docker-compose.yml logs -f api worker"
Write-Host "Para parar tudo: ./stop_local.ps1"
Write-Host "---------------------------------------------------"
