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
Write-Host "[1/4] Carregando variáveis de ambiente..." -ForegroundColor Cyan
Load-DotEnv

# 2. Limpeza (se a flag -Clean for usada)
if ($Clean) {
    Write-Host "[EXTRA] MODO LIMPO: Derrubando contêineres e volumes..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml down -v
}

# ---------------------------------------------------------------------------------
# --- PASSO ADICIONADO AQUI ---
# ---------------------------------------------------------------------------------
# 3. Construir a imagem do sandbox, que é uma dependência para o worker
Write-Host "[2/4] Construindo imagem do sandbox ('devagent-sandbox')..." -ForegroundColor Cyan

$SandboxImage = "devagent-sandbox:latest"
$SandboxDockerfile = "infra/sandbox.Dockerfile"

docker build -t $SandboxImage -f $SandboxDockerfile .

# Verifica se o build da imagem do sandbox foi bem-sucedido
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Falha ao construir a imagem do sandbox. Verifique os logs do Docker." -ForegroundColor Red
    exit 1
}
Write-Host "Imagem do sandbox pronta." -ForegroundColor Green
# ---------------------------------------------------------------------------------

# 4. Subir todos os serviços e deixar o 'depends_on' gerenciar a ordem
Write-Host "[3/4] Iniciando serviços principais (DB, Redis, API, Worker)..." -ForegroundColor Cyan
docker compose -f infra/docker-compose.yml up --build -d

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

# 5. Conclusão
Write-Host "[4/4] Processo concluído! O ambiente está online." -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8001/dashboard" -ForegroundColor White
Write-Host "Para ver os logs: docker compose -f infra/docker-compose.yml logs -f api worker"
Write-Host "Para parar tudo: ./stop_local.ps1"
Write-Host "---------------------------------------------------"