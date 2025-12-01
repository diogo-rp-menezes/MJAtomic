# stop_local.ps1
# Para o ambiente local (Docker Desktop) usando Docker Compose V2 no contexto LOCAL

$ErrorActionPreference = "Stop"

function Print-Log {
    param ([string]$Message, [string]$Color="Cyan")
    Write-Host "[DevAgent] $Message" -ForegroundColor $Color
}

Print-Log "Parando o ambiente DevAgentAtomic local..." "Yellow"

try {
    docker compose -f infra/docker-compose.yml down
    Print-Log "Ambiente local parado com sucesso." "Green"
} catch {
    Print-Log "ERRO: Falha ao parar o ambiente local. Verifique se os contêineres estão rodando ou se o Docker está ativo." "Red"
    Write-Error $_
    exit 1
}
