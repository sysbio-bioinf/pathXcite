#Requires -Version 5
$ErrorActionPreference = 'Stop'

# ===== Local-only config (everything stays in CWD) =====
$PythonVersion   = '3.12'
$MfDir           = '.\miniforge'   # local Miniforge install dir (in CWD)
$VenvDir         = '.\venv'        # local venv dir (in CWD)
$Requirements    = 'requirements.txt'
$TestImportsPy   = 'test_imports.py'
$MainPy          = 'main.py'
$GmtSetupPy      = 'setup_gmt_files.py'

Write-Host "[cwd] $((Get-Location).Path)"
Write-Host "[os]  Windows $([System.Environment]::OSVersion.VersionString)"

function Get-Arch {
    switch ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture) {
        'X64'   { 'x86_64' }
        'Arm64' { 'arm64' }
        default { throw "Unsupported Windows architecture: $($_)" }
    }
}

function Ensure-Miniforge {
    $mfPy = Join-Path $MfDir 'python.exe'
    if (-not (Test-Path $mfPy)) {
        $arch = Get-Arch
        $installer = "Miniforge3-Windows-$arch.exe"
        $url = "https://github.com/conda-forge/miniforge/releases/latest/download/$installer"
        Write-Host "[Miniforge] Downloading $url ..."
        Invoke-WebRequest -Uri $url -UseBasicParsing -OutFile $installer
        if (Test-Path $MfDir) { Remove-Item -Recurse -Force $MfDir }
        $mfFull = [System.IO.Path]::GetFullPath($MfDir)
        Write-Host "[Miniforge] Installing to $mfFull ..."
        Start-Process -FilePath ".\${installer}" -ArgumentList @('/S', "/D=$mfFull") -Wait
        Remove-Item $installer -Force
        Write-Host "[Miniforge] Installed."
    } else {
        Write-Host "[Miniforge] Found at $MfDir"
    }

    # Ensure exact Python version in base env
    $mfPy = Join-Path $MfDir 'python.exe'
    $ver  = & $mfPy -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    if ($ver -ne $PythonVersion) {
        Write-Host "[Miniforge] Installing python=$PythonVersion in base ..."
        $condaBat = Join-Path $MfDir 'condabin\conda.bat'
        & $condaBat install -y "python=$PythonVersion"
        if ($LASTEXITCODE -ne 0) { throw "conda install python=$PythonVersion failed ($LASTEXITCODE)" }
    }
    return $mfPy
}

function Ensure-Venv {
    param([string]$BasePython)
    $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
    if (Test-Path $venvPy) {
        try {
            $v = & $venvPy -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
        } catch { $v = '' }
        if ($v -eq $PythonVersion) {
            Write-Host "[venv] Reusing $VenvDir (Python $v)."
            return $venvPy
        }
        Write-Host "[venv] Wrong/missing version ($v). Recreating ..."
        Remove-Item -Recurse -Force $VenvDir
    }
    Write-Host "[venv] Creating $VenvDir using $BasePython ..."
    & $BasePython -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "python -m venv failed ($LASTEXITCODE)" }
    if (-not (Test-Path $venvPy)) { throw "Venv python missing at $venvPy" }
    return $venvPy
}

function Ensure-Pip {
    param([string]$VenvPython)
    $pipExe = Join-Path $VenvDir 'Scripts\pip.exe'
    if (Test-Path $pipExe) { return }
    Write-Host "[pip] Bootstrapping pip (ensurepip)..."
    & $VenvPython -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[pip] ensurepip unavailable; using get-pip.py ..."
        $tmp = Join-Path $env:TEMP ("get-pip_{0}.py" -f ([Guid]::NewGuid().ToString("N")))
        Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -UseBasicParsing -OutFile $tmp
        & $VenvPython $tmp
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        if ($LASTEXITCODE -ne 0) { throw "get-pip.py failed ($LASTEXITCODE)" }
    }
}

function Install-Requirements {
    param([string]$VenvPython)
    if (-not (Test-Path $Requirements)) { throw "$Requirements not found in $(Get-Location)" }
    Ensure-Pip -VenvPython $VenvPython
    Write-Host "[pip] Upgrading pip/setuptools/wheel ..."
    & $VenvPython -m pip install -U pip setuptools wheel
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed ($LASTEXITCODE)" }
    Write-Host "[pip] Installing from $Requirements ..."
    & $VenvPython -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "pip install -r failed ($LASTEXITCODE)" }

    # Optional visibility:
    & $VenvPython -m pip -V
    & $VenvPython -m pip list
    & $VenvPython -m pip check
}

function Verify-Imports {
    param([string]$VenvPython)
    Write-Host "[verify] Importing required packages ..."
    $code = @'
import importlib, sys
mods = ["numpy","pandas","requests","scipy","statsmodels","PyQt5","PyQt5.QtSvg","PyQt5.QtWebEngineWidgets"]
failed = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        failed.append((m, repr(e)))

# SIP binding as used by PyQt5 wheels:
try:
    from PyQt5 import sip as _sip  # provided by pyqt5-sip
except Exception as e:
    failed.append(("PyQt5.sip", repr(e)))

if failed:
    for n, err in failed:
        print(f"[IMPORT ERROR] {n}: {err}", file=sys.stderr)
    sys.exit(1)
print("All verification imports succeeded.")
'@
    $tmp = Join-Path $env:TEMP ("verify_imports_{0}.py" -f ([Guid]::NewGuid().ToString("N")))
    Set-Content -Path $tmp -Value $code -Encoding UTF8
    try {
        & $VenvPython $tmp
        if ($LASTEXITCODE -ne 0) { throw "verify imports failed ($LASTEXITCODE)" }  # <-- check exit code
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

function Run-IfExists {
    param([string]$VenvPython, [string]$ScriptPath, [string]$Tag)
    if (Test-Path $ScriptPath) {
        Write-Host ("[run] {0}: {1}" -f $Tag, $ScriptPath)
        & $VenvPython $ScriptPath
        if ($LASTEXITCODE -ne 0) { throw "$Tag failed with exit code $LASTEXITCODE" }
    }
}

# ===== Main =====
$mfPy   = Ensure-Miniforge
Write-Host "[info] Local Python: $mfPy ($(& $mfPy -V))"

$venvPy = Ensure-Venv -BasePython $mfPy
Write-Host "[info] Venv Python: $venvPy ($(& $venvPy -V))"

# ------- QUICK CHECK (fix: inspect $LASTEXITCODE) -------
$quickOk = $true
$quick = @'
import importlib
for m in ["numpy","pandas","requests","scipy","statsmodels","PyQt5","PyQt5.QtSvg","PyQt5.QtWebEngineWidgets"]:
    importlib.import_module(m)
from PyQt5 import sip as _sip
'@
$tmpQuick = Join-Path $env:TEMP ("quickcheck_{0}.py" -f ([Guid]::NewGuid().ToString("N")))
Set-Content -Path $tmpQuick -Value $quick -Encoding UTF8
& $venvPy $tmpQuick
if ($LASTEXITCODE -ne 0) { $quickOk = $false }
Remove-Item $tmpQuick -Force -ErrorAction SilentlyContinue

if (-not $quickOk) {
    Install-Requirements -VenvPython $venvPy
}

Verify-Imports -VenvPython $venvPy

Run-IfExists -VenvPython $venvPy -ScriptPath $TestImportsPy -Tag 'test'
Write-Host "[info] Imports check finished ..."
Run-IfExists -VenvPython $venvPy -ScriptPath $GmtSetupPy -Tag 'gmt-setup'
Write-Host "[info] Initial GMT (Gene Set Libraries) downloaded; starting app ..."
& $venvPy $MainPy
