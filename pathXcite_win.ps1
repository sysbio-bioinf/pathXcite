#Requires -Version 5
$ErrorActionPreference = 'Stop'

# ===== Local-only config (everything stays in CWD) =====
$PythonVersion   = '3.12'          # optional: used only for info display
$MfDir           = '.\miniforge'   # expected local Python base (unchanged from your layout)
$VenvDir         = '.\venv'        # expected venv dir (unchanged)
$MainPy          = 'main.py'

Write-Host "[cwd] $((Get-Location).Path)"
Write-Host "[os]  Windows $([System.Environment]::OSVersion.VersionString)"

# --- helpers ---
function Test-ExeRuns {
    param([string]$Path, [string]$Args = '-V')
    if (-not (Test-Path $Path)) { return $false }
    try {
        & $Path $Args | Out-Null
        return $true
    } catch {
        return $false
    }
}

$missing = @()

# 1) Check base Python (your local Miniforge layout)
$basePy = Join-Path $MfDir 'python.exe'
if (-not (Test-ExeRuns -Path $basePy)) {
    $missing += "Python executable not found or not runnable at '$basePy'."
} else {
    $ver = & $basePy -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    Write-Host "[info] Base Python: $basePy (Python $ver)"
}

# 2) Check venv Python
$venvPy = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-ExeRuns -Path $venvPy -Args '-c ""')) {
    if (-not (Test-Path $venvPy)) {
        $missing += "Venv Python not found at '$venvPy'."
    } else {
        $missing += "Venv Python exists but failed to run at '$venvPy'."
    }
} else {
    $vver = & $venvPy -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    Write-Host "[info] Venv Python: $venvPy (Python $vver)"
}

# 3) Check main.py presence
if (-not (Test-Path $MainPy)) {
    $missing += "Main script missing: '$MainPy'."
}

# If anything missing, report and stop
if ($missing.Count -gt 0) {
    Write-Host "`n[ERROR] One or more required components are missing:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

# Optional ultra-quick sanity of venv interpreter (no heavy imports)
try {
    & $venvPy -c "import sys; print('ok')" | Out-Null
} catch {
    Write-Host "[ERROR] Venv Python failed a basic run check." -ForegroundColor Red
    exit 1
}

# 4) Run main
Write-Host "[run] Launching: $MainPy"
& $venvPy $MainPy
$exit = $LASTEXITCODE
if ($exit -ne 0) {
    Write-Host "[exit] main.py finished with exit code $exit."
}
exit $exit
