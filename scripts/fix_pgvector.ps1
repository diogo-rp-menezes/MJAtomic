param(
  [string]$CollectionName
)

function Print-Info($msg) { Write-Host "[fix_pgvector] $msg" -ForegroundColor Cyan }
function Print-Ok($msg)   { Write-Host "[fix_pgvector] $msg" -ForegroundColor Green }
function Print-Warn($msg) { Write-Host "[fix_pgvector] $msg" -ForegroundColor Yellow }
function Print-Err($msg)  { Write-Host "[fix_pgvector] $msg" -ForegroundColor Red }

# Resolve paths
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
  # Preferência: valor efetivo usado nos containers (env_file). .env.compose sobrepõe .env.local.
  $envLocal   = Join-Path $ProjectRoot ".env.local"
  $envCompose = Join-Path $ProjectRoot ".env.compose"
  $name = Get-EnvValueFromFile $envLocal "PGVECTOR_COLLECTION_NAME"
  $nameCompose = Get-EnvValueFromFile $envCompose "PGVECTOR_COLLECTION_NAME"
  if ($nameCompose) { $name = $nameCompose }
  if (-not $name) { $name = "code_collection" }
  $CollectionName = $name
}

Print-Info "Projeto: $ProjectRoot"
Print-Info "Compose: $ComposeFile"
Print-Info "Coleção/Tabela alvo: $CollectionName"

# Garante que o DB está de pé
Print-Info "Garantindo que o serviço 'db' está em execução..."
docker compose -f $ComposeFile up -d db | Out-Null
if ($LASTEXITCODE -ne 0) { Print-Err "Falha ao subir 'db'"; exit 3 }

# Comando para dropar a tabela no Postgres dentro do container do banco (concatenação evita problemas de escape)
$psqlCmd = 'DROP TABLE IF EXISTS public."' + $CollectionName + '" CASCADE;'
Print-Info "Executando DROP no Postgres: $psqlCmd"
docker compose -f $ComposeFile exec -T db psql -U devagent -d devagent_db -p 5433 -c "$psqlCmd"
if ($LASTEXITCODE -ne 0) {
  Print-Warn "Falha ao executar DROP (pode ser que a tabela não exista). Continuando..."
} else {
  Print-Ok "DROP executado com sucesso."
}

# Opcional: reiniciar API/Worker para garantir recriação limpa na próxima inicialização da store
Print-Info "Reiniciando api/worker para recriação da coleção quando necessário..."
docker compose -f $ComposeFile restart api worker | Out-Null

Print-Ok "Concluído. Ao inicializar o PGVectorStore, a tabela será criada novamente com o esquema esperado."
