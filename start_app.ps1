# start_app.ps1
# Script de Inicialização do DevAgentAtomic (Versão Robusta v5 - Suporte a Docker via SSH)
# Autor: Assistente de IA

$ErrorActionPreference = "Stop"
$ProjectRoot = Get-Location

function Print-Log {
    param ([string]$Message, [string]$Color="Cyan")
    Write-Host "[DevAgent] $Message" -ForegroundColor $Color
}

# --- SEÇÃO CORRIGIDA ---
# 0. Configuração do Docker Host (suporta local, TCP e SSH)
if ($env:MJATOMIC_DOCKER_HOST_IP) {
    if ($env:MJATOMIC_DOCKER_USER) {
        # Formato SSH: ssh://usuario@host
        $env:DOCKER_HOST = "ssh://$($env:MJATOMIC_DOCKER_USER)@$($env:MJATOMIC_DOCKER_HOST_IP)"
        Print-Log "Configurado para usar Docker Host via SSH: $($env:DOCKER_HOST)" "Yellow"
    } else {
        # Formato TCP: tcp://host:porta
        $env:DOCKER_HOST = "tcp://$($env:MJATOMIC_DOCKER_HOST_IP):2375"
        Print-Log "Configurado para usar Docker Host via TCP: $($env:DOCKER_HOST)" "Yellow"
    }
} else {
    Print-Log "Usando configuração de Docker local padrão." "Gray"
}
# --- FIM DA SEÇÃO CORRIGIDA ---

# 1. Detectar Python (com prioridade para o ambiente virtual)
$PythonPath = ""
$VenvPythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPythonPath) {
    $PythonPath = $VenvPythonPath
    Print-Log "Python do ambiente virtual detectado: $PythonPath" "Green"
} else {
    try {
        $PythonPath = (Get-Command python).Source
        Print-Log "AVISO: Usando Python global. Ative o ambiente virtual ('./.venv/Scripts/activate') para garantir consistência." "Yellow"
        Print-Log "Python global detectado: $PythonPath" "Gray"
    } catch {
        Print-Log "ERRO: Nenhum Python encontrado (nem no .venv, nem globalmente). Instale o Python ou crie o ambiente virtual." "Red"
        exit
    }
}

# 2. Verificar dependências
Print-Log "Verificando dependências..."
try {
    & $PythonPath -c "import uvicorn; import celery; from dotenv import load_dotenv" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Modules not found" }
} catch {
    Print-Log "ERRO: Dependências faltando. Execute 'poetry install'." "Red"
    exit
}

# 3. .env check
if (-not (Test-Path ".env")) {
    Print-Log "Arquivo .env não encontrado, copiando de .env.example..."
    Copy-Item ".env.example" ".env"
}

# 4. Docker Sandbox Check
Print-Log "Verificando Docker Sandbox..."
try {
    $ImageCheck = docker images -q devagent-sandbox 2>$null
    if (-not $ImageCheck) {
        Print-Log "Criando imagem devagent-sandbox (pode demorar)..." "Yellow"
        if (Test-Path "enable_polyglot.ps1") { ./enable_polyglot.ps1 }
        else { docker build -t devagent-sandbox -f infra/sandbox.Dockerfile . }
    }
} catch {
    Print-Log "ERRO: Falha ao comunicar com o daemon do Docker. Verifique se o Docker está rodando e se as variáveis de ambiente DOCKER_HOST/MJATOMIC_* estão corretas." "Red"
    exit
}


# 5. Infraestrutura
Print-Log "Subindo Banco e Redis..."
docker-compose -f infra/docker-compose.yml up -d
Start-Sleep -Seconds 3

# 6. Worker (Celery)
Print-Log "Iniciando Worker..."
$WorkerScriptBlock = "
    Write-Host 'Iniciando Celery Worker...' -ForegroundColor Cyan;
    cd '$ProjectRoot';
    & '$PythonPath' -m celery -A src.services.celery_worker.worker.celery_app worker --loglevel=info --pool=solo;
    if (`$LASTEXITCODE -ne 0) {
        Write-Host 'ERRO FATAL: O Worker caiu.' -ForegroundColor Red;
        Read-Host 'Pressione ENTER para sair...';
    }
"
$EncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($WorkerScriptBlock))
Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", "$EncodedCommand" -WorkingDirectory $ProjectRoot

# 7. API (Uvicorn)
Print-Log "Iniciando API (Porta 8001)..."
$ApiScriptBlock = "
    Write-Host 'Iniciando API...' -ForegroundColor Green;
    cd '$ProjectRoot';
    & '$PythonPath' -m uvicorn src.services.api_gateway.main:app --reload --port 8001;
    if (`$LASTEXITCODE -ne 0) { Read-Host 'Erro na API. Pressione ENTER...'; }
"
$EncodedApi = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($ApiScriptBlock))
Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", "$EncodedApi" -WorkingDirectory $ProjectRoot

# 8. Final
Print-Log "---------------------------------------------------" "Green"
Print-Log "SISTEMA ONLINE (Porta 8001) 🚀" "Green"
Print-Log "Dashboard: http://127.0.0.1:8001/dashboard/index.html" "White"
Print-Log "---------------------------------------------------" "Green"
