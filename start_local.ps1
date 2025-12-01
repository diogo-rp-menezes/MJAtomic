# start_local.ps1
# Sobe o ambiente local (Docker Desktop) usando Docker Compose V2 no contexto LOCAL

$ErrorActionPreference = "Stop"
$ProjectRoot = Get-Location

function Print-Log {
    param ([string]$Message, [string]$Color="Cyan")
    Write-Host "[DevAgent] $Message" -ForegroundColor $Color
}

# Carrega .env no ambiente do PowerShell (útil para chaves etc.)
function Load-DotEnv {
    param ([string]$Path = (Join-Path $ProjectRoot ".env"))
    if (-not (Test-Path $Path)) {
        Write-Host "[DevAgent] AVISO: Arquivo .env não encontrado. Usando apenas variáveis de ambiente existentes." -ForegroundColor Yellow
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and $line -notmatch "^\s*#") {
            $parts = $line -split "=", 2
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                $value = $value -replace '^"|"$' -replace "^'|'$"
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Write-Host "[DevAgent] Configurações do arquivo .env carregadas." -ForegroundColor Gray
}

# 1) Garantir existência do .env e carregar
if (-not (Test-Path ".env")) {
    Print-Log "Arquivo .env não encontrado, copiando de .env.example..."
    Copy-Item ".env.example" ".env"
}
Load-DotEnv

# 2) Subindo todos os serviços localmente com Docker Compose V2 (sem contexto remoto)
Print-Log "Subindo serviços (DB, Redis, API, Worker) localmente..." "Cyan"
try {
    docker compose -f infra/docker-compose.yml up --build -d
    Print-Log "Serviços iniciados em background no Docker Desktop." "Green"
} catch {
    Print-Log "ERRO: Falha ao iniciar os serviços com Docker Compose local." "Red"
    Write-Error $_
    exit 1
}

# 3) Final
$hostIp = "localhost"
Print-Log "---------------------------------------------------" "Green"
Print-Log "SISTEMA ONLINE (Porta 8001) 🚀" "Green"
Print-Log ("Dashboard: http://{0}:8001/dashboard/index.html" -f $hostIp) "White"
Print-Log "---------------------------------------------------" "Green"
Print-Log "Para ver os logs: docker compose -f infra/docker-compose.yml logs -f" "White"
Print-Log "Para parar tudo: ./stop_local.ps1" "White"
