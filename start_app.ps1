# start_app.ps1
# Script de Inicialização do DevAgentAtomic (Versão Robusta v7 - Leitura de .env)
# Autor: Assistente de IA

$ErrorActionPreference = "Stop"
$ProjectRoot = Get-Location

# --- NOVA FUNÇÃO ---
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
                # Remove aspas do valor, se existirem
                $value = $value -replace '^"|"$' -replace "^'|'$"
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Write-Host "[DevAgent] Configurações do arquivo .env carregadas." -ForegroundColor Gray
}
# --- FIM DA NOVA FUNÇÃO ---

# --- BLOCO DE INICIALIZAÇÃO ---
Load-DotEnv # Carrega as variáveis do .env no início de tudo
# --- FIM DO BLOCO ---

function Print-Log {
    param ([string]$Message, [string]$Color="Cyan")
    Write-Host "[DevAgent] $Message" -ForegroundColor $Color
}

# 0. Configuração do Docker Host (agora lido do .env)
if ($env:MJATOMIC_DOCKER_HOST_IP) {
    if ($env:MJATOMIC_DOCKER_USER) {
        $env:DOCKER_HOST = "ssh://$($env:MJATOMIC_DOCKER_USER)@$($env:MJATOMIC_DOCKER_HOST_IP)"
        Print-Log "Configurado para usar Docker Host via SSH: $($env:DOCKER_HOST)" "Yellow"
    } else {
        $env:DOCKER_HOST = "tcp://$($env:MJATOMIC_DOCKER_HOST_IP):2375"
        Print-Log "Configurado para usar Docker Host via TCP: $($env:DOCKER_HOST)" "Yellow"
    }
} else {
    Print-Log "Usando configuração de Docker local padrão." "Gray"
}

# 1. Detectar Python
$PythonPath = ""
$VenvPythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPythonPath) {
    $PythonPath = $VenvPythonPath
    Print-Log "Python do ambiente virtual detectado: $PythonPath" "Green"
} else {
    try {
        $PythonPath = (Get-Command python).Source
        Print-Log "AVISO: Usando Python global." "Yellow"
    } catch {
        Print-Log "ERRO: Nenhum Python encontrado." "Red"
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

# 3. .env check (agora apenas para copiar se não existir)
if (-not (Test-Path ".env")) {
    Print-Log "Arquivo .env não encontrado, copiando de .env.example..."
    Copy-Item ".env.example" ".env"
    Load-DotEnv # Recarrega após copiar
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
    Print-Log "ERRO: Falha ao comunicar com o daemon do Docker." "Red"
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
    & '$PythonPath' -m celery -A src.services.celery_worker.worker:app worker --loglevel=info --pool=solo;
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
