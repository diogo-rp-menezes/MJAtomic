# start_local.ps1
# Ponto de entrada principal para iniciar o ambiente de desenvolvimento local.

param (
    [switch]$Clean = $false
)

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
    Write-Host "[1/3] MODO LIMPO: Derrubando contêineres e volumes..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml down -v
}

# 3. Subir todos os serviços e deixar o 'depends_on' gerenciar a ordem
Write-Host "[2/3] Iniciando todos os serviços (DB, Redis, Ollama, API, Worker)..." -ForegroundColor Cyan
docker compose -f infra/docker-compose.yml up --build -d

# Loop para esperar o PostgreSQL ficar pronto (ainda uma boa prática)
$max_retries = 20
$retry_count = 0
$db_ready = $false

Write-Host "Aguardando conexão com o banco de dados..." -NoNewline
do {
    try {
        $logs = docker logs devagent_db 2>&1
        if ($logs -match "database system is ready to accept connections") {
            $db_ready = $true
            Write-Host ""
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
    Write-Host ""
    Write-Host "ERRO: Banco de dados não iniciou a tempo." -ForegroundColor Red
    exit 1
}

# 4. Conclusão
Write-Host "[3/3] Processo concluído! O ambiente está online." -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8001/dashboard" -ForegroundColor White
Write-Host "Para ver os logs: docker compose -f infra/docker-compose.yml logs -f api worker"
Write-Host "Para parar tudo: ./stop_local.ps1"
Write-Host "---------------------------------------------------"
