# stop_app.ps1
# Script para parar o ambiente DevAgentAtomic (Compose V2 + SSH Context)

$ErrorActionPreference = "Stop"

function Print-Log {
    param ([string]$Message, [string]$Color="Cyan")
    Write-Host "[DevAgent] $Message" -ForegroundColor $Color
}

Print-Log "Parando o ambiente DevAgentAtomic no host remoto..." "Yellow"

try {
    docker --context remote-ssh compose -f infra/docker-compose.yml down
    Print-Log "Ambiente parado com sucesso (remoto)." "Green"
} catch {
    Print-Log "ERRO: Falha ao parar o ambiente remoto. Verifique se os contêineres estão rodando ou se o Docker está ativo." "Red"
    Write-Error $_
    exit 1
}
