function Print-Info($msg) { Write-Host "[init_pgvector] $msg" -ForegroundColor Cyan }
function Print-Ok($msg)   { Write-Host "[init_pgvector] $msg" -ForegroundColor Green }
function Print-Err($msg)  { Write-Host "[init_pgvector] $msg" -ForegroundColor Red }

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ComposeFile = Join-Path $ProjectRoot "infra\docker-compose.yml"

if (!(Test-Path $ComposeFile)) { Print-Err "docker-compose.yml não encontrado em $ComposeFile"; exit 2 }

Print-Info "Garantindo que o serviço 'db' está em execução..."
docker compose -f $ComposeFile up -d db | Out-Null
if ($LASTEXITCODE -ne 0) { Print-Err "Falha ao subir 'db'"; exit 3 }

Print-Info "Criando extensão pgvector (se necessário)..."
docker compose -f $ComposeFile exec -T db psql -U devagent -d devagent_db -p 5433 -c "CREATE EXTENSION IF NOT EXISTS vector;"
if ($LASTEXITCODE -ne 0) {
  Print-Err "Falha ao criar extensão 'vector'"
  exit 4
}

Print-Ok "Extensão 'vector' disponível."
