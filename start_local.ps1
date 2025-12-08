# start_local.ps1
# Ponto de entrada principal para iniciar o ambiente de desenvolvimento local.

param (
    [switch]$Clean = $false
)

# Garante que o script pare em erros inesperados
$ErrorActionPreference = "Stop"

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
Write-Host "[1/5] Carregando variáveis de ambiente..." -ForegroundColor Cyan
Load-DotEnv

# 2. Limpeza (se a flag -Clean for usada)
if ($Clean) {
    Write-Host "[EXTRA] MODO LIMPO: Derrubando contêineres e volumes..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml down -v
}

# 3. Construir a imagem do sandbox, que é uma dependência para o worker
Write-Host "[2/5] Construindo imagem do sandbox ('devagent-sandbox')..." -ForegroundColor Cyan
docker build -t "devagent-sandbox:latest" -f "infra/sandbox.Dockerfile" .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Falha ao construir a imagem do sandbox. Verifique os logs do Docker." -ForegroundColor Red
    exit 1
}
Write-Host "Imagem do sandbox pronta." -ForegroundColor Green

# 4. Subir todos os serviços
Write-Host "[3/5] Iniciando serviços principais (DB, Redis, API, Worker)..." -ForegroundColor Cyan
docker compose -f infra/docker-compose.yml up --build -d

# 5. Esperar e Verificar o Banco de Dados
Write-Host "[4/5] Aguardando e verificando o banco de dados..." -ForegroundColor Cyan

# Loop para esperar o PostgreSQL ficar pronto
$max_retries_db_ready = 30
$retry_count_db_ready = 0
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
            Start-Sleep -Seconds 2
            $retry_count_db_ready++
        }
    } catch {
        Write-Host "x" -NoNewline
        Start-Sleep -Seconds 2
        $retry_count_db_ready++
    }
} while (-not $db_ready -and $retry_count_db_ready -lt $max_retries_db_ready)

if (-not $db_ready) {
    Write-Host ""
    Write-Host "ERRO: Banco de dados não iniciou a tempo." -ForegroundColor Red
    exit 1
}

# --- VERIFICAÇÃO DE ESQUEMA DO BANCO DE DADOS (COM RETENTATIVAS) ---
Write-Host "Verificando esquema da tabela de vetores (PGVector)..." -ForegroundColor Cyan

$dbUser = $env:POSTGRES_USER
$dbName = $env:POSTGRES_DB
$collectionName = "langchain_pg_collection" # Nome padrão da tabela do PGVectorStore

$max_retries_schema = 10
$retry_count_schema = 0
$schema_ok = $false

do {
    $sqlCheck = "SELECT 1 FROM information_schema.columns WHERE table_name='$collectionName' AND column_name='langchain_id'"
    $checkCommand = "psql -U $dbUser -d $dbName -t -c ""$sqlCheck"" "

    # Executa o comando dentro do contêiner do DB e captura o resultado
    $result_output = docker exec devagent_db bash -c $checkCommand 2>&1

    # Verifica se o comando foi bem-sucedido e se a saída contém '1'
    if ($LASTEXITCODE -eq 0 -and $result_output.Trim() -eq '1') {
        $schema_ok = $true
    } else {
        # Verifica se a tabela ainda não existe, o que é OK na primeira execução
        if ($result_output -match "relation ""$collectionName"" does not exist") {
            Write-Host "Tabela '$collectionName' ainda não existe, será criada pela aplicação. Verificação OK." -ForegroundColor Green
            $schema_ok = $true
        } else {
            Write-Host "Aguardando esquema do banco de dados... ($($retry_count_schema+1)/$max_retries_schema)" -NoNewline
            Start-Sleep -Seconds 3
            $retry_count_schema++
        }
    }
} while (-not $schema_ok -and $retry_count_schema -lt $max_retries_schema)

if (-not $schema_ok) {
    Write-Host ""
    Write-Host "--------------------------------------------------------" -ForegroundColor Red
    Write-Host " ERRO CRÍTICO DE INCOMPATIBILIDADE DE BANCO DE DADOS!" -ForegroundColor Red
    Write-Host "--------------------------------------------------------" -ForegroundColor Yellow
    Write-Host "Causa: A tabela '$collectionName' foi encontrada, mas está usando um esquema antigo (sem a coluna 'langchain_id')."
    Write-Host "Isso impede que a memória do agente funcione e causa falhas em cascata."
    Write-Host ""
    Write-Host "SOLUÇÃO DEFINITIVA:" -ForegroundColor Green
    Write-Host "Para corrigir, execute o seguinte comando e rode o ./start_local.ps1 novamente:"
    Write-Host ""
    Write-Host "1. Para destruir o banco de dados antigo:" -ForegroundColor Cyan
    Write-Host "   docker compose -f infra/docker-compose.yml down -v" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Para reiniciar o ambiente (que irá recriar o banco corretamente):" -ForegroundColor Cyan
    Write-Host "   ./start_local.ps1" -ForegroundColor White
    Write-Host "--------------------------------------------------------"
    exit 1
}
# --- FIM DA VERIFICAÇÃO ---

# 6. Conclusão
Write-Host "[5/5] Processo concluído! O ambiente está online." -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8001/dashboard" -ForegroundColor White
Write-Host "Para ver os logs: docker compose -f infra/docker-compose.yml logs -f api worker"
Write-Host "Para parar tudo: ./stop_local.ps1"
Write-Host "---------------------------------------------------"