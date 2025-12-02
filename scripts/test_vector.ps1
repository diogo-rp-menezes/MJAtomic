function Print-Info($msg) { Write-Host "[test_vector] $msg" -ForegroundColor Cyan }
function Print-Err($msg)  { Write-Host "[test_vector] $msg" -ForegroundColor Red }
function Print-Ok($msg)   { Write-Host "[test_vector] $msg" -ForegroundColor Green }

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ComposeFile = Join-Path $ProjectRoot "infra\docker-compose.yml"

if (!(Test-Path $ComposeFile)) { Print-Err "docker-compose.yml não encontrado em $ComposeFile"; exit 2 }

Print-Info "Subindo api para o teste..."
docker compose -f $ComposeFile up -d api | Out-Null
if ($LASTEXITCODE -ne 0) { Print-Err "Falha ao subir 'api'"; exit 3 }

Print-Info "Executando quick_test_vector dentro do container api..."
docker compose -f $ComposeFile exec -T api python /app/scripts/quick_test_vector.py
if ($LASTEXITCODE -ne 0) {
  Print-Err "Teste falhou. Verifique os logs do container api."
  exit 4
}

Print-Ok "Teste do PGVector concluído com sucesso."
