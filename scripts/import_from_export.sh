#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_FILE="$ROOT_DIR/export/conversations.json"
VENV_DIR="$ROOT_DIR/.venv"
REQ_FILE="$ROOT_DIR/scripts/requirements.txt"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtualenv in $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m ensurepip --upgrade >/dev/null
fi

source "$VENV_DIR/bin/activate"

if [[ -f "$REQ_FILE" ]]; then
  echo "Installing dependencies into venv ..."
  "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
  "$VENV_DIR/bin/pip" install -r "$REQ_FILE"
fi

if [[ ! -f "$EXPORT_FILE" ]]; then
  echo "Export file not found: $EXPORT_FILE" >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY not set. Load your .env or export it before running." >&2
  exit 1
fi

echo "Importing recipes from $EXPORT_FILE ..."
python -u "$ROOT_DIR/scripts/import_conversations.py"

echo "Normalizing categories/tags to Russian ..."
python "$ROOT_DIR/scripts/translate_categories.py"

echo "Generating images ..."
python "$ROOT_DIR/scripts/generate_images.py"

echo "Rebuilding menu ..."
python "$ROOT_DIR/scripts/rebuild_menu.py"

echo "Done. Recipes are in $ROOT_DIR/recipes"
