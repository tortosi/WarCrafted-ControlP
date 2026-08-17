#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== WarCrafted-ControlP - Instalador (Linux) ==="

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 no esta instalado."
  echo "Instalalo con: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
  exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "Python detectado: $PYTHON_VERSION"

if [ ! -d ".venv" ]; then
  echo "Creando entorno virtual (.venv)..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Instalando dependencias..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

if [ ! -f ".env" ]; then
  echo "Creando archivo .env a partir de .env.example..."
  cp .env.example .env
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  if [[ "${OSTYPE:-}" == darwin* ]]; then
    sed -i '' "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
  else
    sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
  fi
  echo "Se genero una SECRET_KEY aleatoria en .env."
else
  echo ".env ya existe, no se sobrescribe."
fi

mkdir -p data

echo
echo "=== Creacion del usuario administrador ==="
read -rp "Usuario administrador [admin]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}
read -rsp "Contrasena: " ADMIN_PASS
echo
python -m app.cli create-admin --username "$ADMIN_USER" --password "$ADMIN_PASS"

echo
echo "Instalacion completada."
echo "Edita el archivo .env para configurar tus instancias de emulador antes de arrancar."
echo "Para iniciar el panel ejecuta: ./run.sh"
