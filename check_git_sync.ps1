# check_git_sync.ps1
# Verifica rapidamente a sincronização da branch atual com o upstream (ex.: origin/main)

$ErrorActionPreference = "Stop"

function Print-Log {
    param ([string]$Message, [string]$Color = "Cyan")
    Write-Host "[GitSync] $Message" -ForegroundColor $Color
}

function Run-Git {
    param([string]$Args)
    $out = git $Args 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git $Args falhou: $out" }
    return ($out | Out-String).Trim()
}

try {
    if (-not (Test-Path ".git")) {
        throw "Este script deve ser executado na raiz de um repositório Git (pasta contendo .git)."
    }

    $branch = Run-Git "rev-parse --abbrev-ref HEAD"

    # Descobrir upstream (ex.: origin/main)
    $upstream = $null
    try { $upstream = Run-Git "rev-parse --abbrev-ref --symbolic-full-name @{u}" } catch {}

    if (-not $upstream) {
        Print-Log "A branch '$branch' não possui um upstream configurado." "Yellow"
        Print-Log "Configure com: git branch --set-upstream-to origin/$branch $branch" "Yellow"
        exit 2
    }

    Print-Log "Repositório: $(Run-Git 'remote get-url origin')" "Gray"
    Print-Log "Branch atual: $branch | Upstream: $upstream" "Gray"

    # Buscar últimas refs
    Print-Log "Atualizando refs do remoto (git fetch)..." "Cyan"
    git fetch origin | Out-Null

    # ahead/behind em relação ao upstream
    # Formato: "BEHIND\tAHEAD" quando usamos "$upstream...HEAD"
    $counts = Run-Git "rev-list --left-right --count $upstream...HEAD"
    $parts = $counts -split "\s+"
    $behind = [int]$parts[0]
    $ahead  = [int]$parts[1]

    # Status curto da árvore de trabalho
    $status = Run-Git "status -b -uno"

    Print-Log "---------------------- RESUMO ----------------------" "Green"
    Write-Host $status
    Write-Host ""
    if ($behind -eq 0 -and $ahead -eq 0) {
        Print-Log "Sua branch '$branch' está sincronizada com '$upstream'." "Green"
    } else {
        if ($behind -gt 0) { Print-Log ("Está {0} commit(s) ATRÁS de {1}. Faça: git pull --rebase" -f $behind, $upstream) "Yellow" }
        if ($ahead -gt 0)  { Print-Log ("Está {0} commit(s) À FRENTE de {1}. Faça: git push" -f $ahead, $upstream) "Yellow" }
    }
    Print-Log "----------------------------------------------------" "Green"

    # Código de saída amigável: 0=sincronizado, 10=ahead, 11=behind, 12=ahead+behind
    if ($behind -eq 0 -and $ahead -eq 0) { exit 0 }
    elseif ($behind -eq 0) { exit 10 }
    elseif ($ahead -eq 0) { exit 11 }
    else { exit 12 }

} catch {
    Print-Log "Erro: $_" "Red"
    exit 1
}
