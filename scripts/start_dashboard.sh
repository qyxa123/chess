#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR=".venv_dashboard"
PYTHON_BIN="${PYTHON:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python is required. Please install Python 3.8+ and rerun this script."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip

install_requirements() {
  local req_file="$1"
  if [ -f "$req_file" ]; then
    if ! pip install -r "$req_file"; then
      echo "Failed to install dependencies from $req_file"
      echo "You can install manually with: pip install -r $req_file"
      exit 1
    fi
  fi
}

install_requirements "requirements_computer.txt"
install_requirements "requirements_dashboard.txt"

exec streamlit run dashboard_local/app.py
