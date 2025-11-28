# start_app.ps1
# Script de Inicialização do DevAgentAtomic (Versão Robusta v2)
# Configurado para PORTA 8001 e Worker Estável
# Autor: Assistente de IA

$ErrorActionPreference = "Stop"
$ProjectRoot = Get-Location

function Print-Log {
    param ([string]$Message, [string]$Color="Cyan")
    Write-Host "[DevAgent] $Message" -ForegroundColor $Color
}

# 1. Detectar Python
try {
    $PythonPath = (Get-Command python).Source
    Print-Log "Python detectado: $PythonPath" "Gray"
} catch {
    Print-Log "ERRO: Python não encontrado. Ative o venv." "Red"
    exit
}

# 2. Verificar dependências
Print-Log "Verificando dependências..."
try {
    & $PythonPath -c "import uvicorn; import celery; from dotenv import load_dotenv" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Modules not found" }
} catch {
    Print-Log "ERRO: Dependências faltando. Execute 'poetry install' ou 'pip install ...'" "Red"
    exit
}

# 3. .env check
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

# 4. Docker Sandbox Check
Print-Log "Verificando Docker Sandbox..."
$ImageCheck = docker images -q devagent-sandbox 2>$null
if (-not $ImageCheck) {
    Print-Log "Criando imagem devagent-sandbox (pode demorar)..." "Yellow"
    # Verifica se o enable_polyglot já rodou para termos o Dockerfile certo
    if (Test-Path "enable_polyglot.ps1") { ./enable_polyglot.ps1 }
    else { docker build -t devagent-sandbox -f infra/sandbox.Dockerfile . }
}

# 5. Infraestrutura
Print-Log "Subindo Banco e Redis..."
docker-compose -f infra/docker-compose.yml up -d
Start-Sleep -Seconds 3

# 6. Worker (Celery) - CORREÇÃO AQUI
Print-Log "Iniciando Worker..."
# O comando agora inclui um 'try/catch' interno no powershell filho para não fechar a janela em caso de erro imediato
$WorkerScriptBlock = "
    Write-Host 'Iniciando Celery Worker...' -ForegroundColor Cyan;
    cd '$ProjectRoot';
    & '$PythonPath' -m celery -A src.services.celery_worker.worker.celery_app worker --loglevel=info --pool=solo;
    if (`$LASTEXITCODE -ne 0) {
        Write-Host 'ERRO FATAL: O Worker caiu.' -ForegroundColor Red;
        Read-Host 'Pressione ENTER para sair...';
    }
"
# Codifica o comando para evitar problemas de aspas
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