#!/usr/bin/env bash
set -Eeuo pipefail

# ===== Local-only config (everything stays in CWD) =====
REQUIRED_PY="3.12"
MF_DIR="./miniforge"     # local Miniforge install dir (in CWD)
VENV_DIR="./venv"        # local venv dir (in CWD)
REQ_FILE="requirements.txt"
TEST_IMPORTS_SCRIPT="test_imports.py"
MAIN_SCRIPT="main.py"
GMT_SETUP_SCRIPT="setup_gmt_files.py"  # script to setup initial GMT files
# VERIFY:
VERIFY_PKGS=("numpy" "pandas" "requests" "scipy" "statsmodels" "PyQt5" "PyQt5.QtSvg" "PyQt5.QtWebEngineWidgets")
SHEBANG_MAX=127

# ----- logging (stderr) & helpers -----
log(){ printf '%s\n' "$*" >&2; }
die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }

OS="$(uname -s || true)"
ARCH="$(uname -m || true)"

mf_python() { printf '%s\n' "${MF_DIR}/bin/python3"; }
mf_conda()  { printf '%s\n' "${MF_DIR}/bin/conda"; }
venv_python_path() {
  case "$OS" in
    MINGW*|MSYS*|CYGWIN*) printf '%s\n' "${VENV_DIR}/Scripts/python.exe" ;;
    *)                    printf '%s\n' "${VENV_DIR}/bin/python" ;;
  esac
}
python_xy() { "$1" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'; }

check_path_length() {
  local p="$1" n=${#1}
  if [ "$n" -gt "$SHEBANG_MAX" ]; then
    log "WARNING: interpreter path length ($n) > ~$SHEBANG_MAX may hit shebang limits."
    log "Path: $p"
  fi
}

# ----- 1) Ensure local Miniforge exists in ./miniforge with Python 3.12 -----
ensure_local_miniforge() {
  if [ ! -x "${MF_DIR}/bin/python3" ]; then
    log "[Miniforge] Not found in ${MF_DIR}; installing locally..."
    local inst
    case "$OS" in
      Darwin)
        case "$ARCH" in
          arm64)  inst="Miniforge3-MacOSX-arm64.sh" ;;
          x86_64) inst="Miniforge3-MacOSX-x86_64.sh" ;;
          *) die "Unsupported macOS arch: $ARCH" ;;
        esac
        ;;
      Linux)
        case "$ARCH" in
          x86_64)  inst="Miniforge3-Linux-x86_64.sh" ;;
          aarch64) inst="Miniforge3-Linux-aarch64.sh" ;;
          *) die "Unsupported Linux arch: $ARCH" ;;
        esac
        ;;
      MINGW*|MSYS*|CYGWIN*) die "Native Windows bash detected. Use WSL or a PowerShell flow." ;;
      *) die "Unsupported OS: $OS" ;;
    esac

    local url="https://github.com/conda-forge/miniforge/releases/latest/download/${inst}"
    log "[Miniforge] Downloading ${url} ..."
    curl -fsSL -o "$inst" "$url" 1>&2 || die "Failed to download Miniforge installer"
    chmod +x "$inst" 1>&2
    [ -d "$MF_DIR" ] && rm -rf "$MF_DIR" 1>&2
    "./$inst" -b -p "$MF_DIR" 1>&2
    rm -f "$inst" 1>&2
    log "[Miniforge] Installed into ${MF_DIR}."
  else
    log "[Miniforge] Found at ${MF_DIR}."
  fi

  if [ "$("$(mf_python)" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || true)" != "$REQUIRED_PY" ]; then
    log "[Miniforge] Installing Python ${REQUIRED_PY} locally..."
    "$(mf_conda)" install -y "python=${REQUIRED_PY}" 1>&2
  fi

  mf_python   # print path only to stdout
}

# ----- 2) Create or reuse local venv at ./venv using local Miniforge Python -----
create_or_reuse_venv() {
  local pycmd="$1"   # MUST be ./miniforge/bin/python3
  if [ -d "$VENV_DIR" ]; then
    local vpy; vpy="$(venv_python_path)"
    if [ -x "$vpy" ] && [ "$(python_xy "$vpy" 2>/dev/null || true)" = "$REQUIRED_PY" ]; then
      log "[venv] Reusing ${VENV_DIR} (Python $(python_xy "$vpy"))."
      printf '%s\n' "$vpy"; return 0
    fi
    log "[venv] Existing venv wrong/missing version; recreating..."
    rm -rf "$VENV_DIR" 1>&2
  fi

  log "[venv] Creating ${VENV_DIR} with ${pycmd} (using --copies)..."
  "$pycmd" -m venv --copies "$VENV_DIR" 1>&2

  local vpy; vpy="$(venv_python_path)"
  [ -x "$vpy" ] || die "Venv python missing at $vpy"
  local abs="$(cd "$(dirname "$vpy")" && pwd)/$(basename "$vpy")"
  check_path_length "$abs"
  printf '%s\n' "$vpy"
}

# ----- 3) Install requirements locally into the venv -----
install_requirements() {
  local vpy="$1"
  [ -f "$REQ_FILE" ] || die "$REQ_FILE not found in $(pwd)"
  log "[pip] Upgrading pip/setuptools/wheel ..."
  "$vpy" -m pip install -U pip setuptools wheel 1>&2
  log "[pip] Installing from $REQ_FILE ..."
  "$vpy" -m pip install -r "$REQ_FILE" 1>&2
  "$vpy" -m pip list
}

# ----- 4) Verify imports inside the local venv -----
verify_imports() {
  local vpy="$1"
  log "[verify] Importing required packages..."
  local pylist="["; local first=1
  for p in "${VERIFY_PKGS[@]}"; do
    [ $first -eq 0 ] && pylist+=", "
    pylist+="\"$p\""; first=0
  done
  pylist+="]"

  "$vpy" - <<PY
import importlib, sys
pkgs = ${pylist}
failed = []
for name in pkgs:
    try:
        importlib.import_module(name)
    except Exception as e:
        failed.append((name, repr(e)))
if failed:
    for n, err in failed:
        print(f"[IMPORT ERROR] {n}: {err}", file=sys.stderr)
    sys.exit(1)
print("All verification imports succeeded.")
PY
}

run_test_imports_script() {
  local vpy="$1"
  [ -f "$TEST_IMPORTS_SCRIPT" ] || die "$TEST_IMPORTS_SCRIPT not found in $(pwd)"
  log "[run] $TEST_IMPORTS_SCRIPT"
  "$vpy" "$TEST_IMPORTS_SCRIPT"
  local rc=$?
  if [ $rc -ne 0 ]; then
    die "Test imports script failed with exit code $rc"
  fi
}

# ----- 5) Install initial GMT files -----
install_initial_gmt() {
  local vpy="$1"
  [ -f "$GMT_SETUP_SCRIPT" ] || die "$GMT_SETUP_SCRIPT not found in $(pwd)"
  log "[run] $GMT_SETUP_SCRIPT"
  "$vpy" "$GMT_SETUP_SCRIPT"  
}


# ----- 6) Run main.py with the local venv Python -----
run_main() {
  local vpy="$1"
  [ -f "$MAIN_SCRIPT" ] || die "$MAIN_SCRIPT not found in $(pwd)"
  log "[run] $MAIN_SCRIPT"
  exec "$vpy" "$MAIN_SCRIPT"
}

# ===================== Main (strictly local) =====================
log "[cwd] $(pwd)"
log "[os]  $OS $ARCH"

LOCAL_PY="$(ensure_local_miniforge)"
log "[info] Local Python: $LOCAL_PY ($("$LOCAL_PY" -V 2>/dev/null || true))"

VENV_PY="$(create_or_reuse_venv "$LOCAL_PY")"
log "[info] Venv Python: $VENV_PY ($("$VENV_PY" -V 2>/dev/null || true))"

# If imports fail, install requirements; then verify again
if ! "$VENV_PY" - <<'PY' >/dev/null 2>&1
import importlib
for _n in ["numpy","pandas","requests","scipy","statsmodels","PyQt5","PyQt5.QtSvg","PyQt5.QtWebEngineWidgets"]:
    importlib.import_module(_n)
PY
then
  install_requirements "$VENV_PY"
fi

verify_imports "$VENV_PY"
run_test_imports_script "$VENV_PY"
log "[info] Imports check finished; installing initial GMT files..."
install_initial_gmt "$VENV_PY"
log "[info] Setup complete; launching pathXcite..."
run_main "$VENV_PY"
