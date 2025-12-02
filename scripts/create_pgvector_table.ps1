param(
  [string]$CollectionName,
  [int]$EmbeddingDim
)

function Print-Info($msg) { Write-Host "[create_pgvector_table] $msg" -ForegroundColor Cyan }
function Print-Ok($msg)   { Write-Host "[create_pgvector_table] $msg" -ForegroundColor Green }
function Print-Err($msg)  { Write-Host "[create_pgvector_table] $msg" -ForegroundColor Red }

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ComposeFile = Join-Path $ProjectRoot "infra\docker-compose.yml"

if (!(Test-Path $ComposeFile)) { Print-Err "docker-compose.yml não encontrado em $ComposeFile"; exit 2 }

function Get-EnvValueFromFile([string]$filePath, [string]$key) {
  if (!(Test-Path $filePath)) { return $null }
  $line = (Get-Content $filePath | Where-Object { $_ -match "^$key\s*=\s*" } | Select-Object -Last 1)
  if ($null -ne $line) {
    $value = $line -replace "^$key\s*=\s*", ""
    return $value.Trim().Trim('"').Trim("'")
  }
  return $null
}

if (-not $CollectionName) {
  $envLocal   = Join-Path $ProjectRoot ".env.local"
  $envCompose = Join-Path $ProjectRoot ".env.compose"
  $name = Get-EnvValueFromFile $envLocal "PGVECTOR_COLLECTION_NAME"
  $nameCompose = Get-EnvValueFromFile $envCompose "PGVECTOR_COLLECTION_NAME"
  if ($nameCompose) { $name = $nameCompose }
  if (-not $name) { $name = "code_collection" }
  $CollectionName = $name
}

if (-not $EmbeddingDim -or $EmbeddingDim -le 0) {
  $envLocal   = Join-Path $ProjectRoot ".env.local"
  $envCompose = Join-Path $ProjectRoot ".env.compose"
  $dim = Get-EnvValueFromFile $envLocal "EMBEDDING_DIM"
  $dimCompose = Get-EnvValueFromFile $envCompose "EMBEDDING_DIM"
  if ($dimCompose) { $dim = $dimCompose }
  if (-not $dim) { $dim = 768 }
  $EmbeddingDim = [int]$dim
}

Print-Info "Projeto: $ProjectRoot"
Print-Info "Compose: $ComposeFile"
Print-Info "Tabela: $CollectionName | Dimensão: $EmbeddingDim"

# Garante DB e extensão vector
Print-Info "Garantindo que o serviço 'db' está em execução..."
docker compose -f $ComposeFile up -d db | Out-Null
if ($LASTEXITCODE -ne 0) { Print-Err "Falha ao subir 'db'"; exit 3 }

Print-Info "Criando extensão pgvector (se necessário)..."
docker compose -f $ComposeFile exec -T db psql -U devagent -d devagent_db -p 5433 -c "CREATE EXTENSION IF NOT EXISTS vector;" | Out-Null
if ($LASTEXITCODE -ne 0) { Print-Err "Falha ao criar extensão 'vector'"; exit 4 }

# Cria tabela com o esquema esperado pelo langchain-postgres v0.0.16 (apenas tabela; índices opcionais)
$tableQuoted = 'public."' + $CollectionName + '"'
$createTable = "CREATE TABLE IF NOT EXISTS $tableQuoted ( langchain_id TEXT PRIMARY KEY, content TEXT, embedding VECTOR($EmbeddingDim), langchain_metadata JSONB );"

Print-Info "Criando tabela se não existir..."
docker compose -f $ComposeFile exec -T db psql -U devagent -d devagent_db -p 5433 -c "$createTable"
if ($LASTEXITCODE -ne 0) { Print-Err "Falha ao criar tabela $CollectionName"; exit 5 }

Print-Ok "Tabela pronta: $CollectionName"
