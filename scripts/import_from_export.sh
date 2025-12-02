#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_FILE="$ROOT_DIR/export/conversations.json"

if [[ ! -f "$EXPORT_FILE" ]]; then
  echo "Export file not found: $EXPORT_FILE" >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY not set. Load your .env or export it before running." >&2
  exit 1
fi

echo "Importing recipes from $EXPORT_FILE ..."
python "$ROOT_DIR/scripts/import_conversations.py"

echo "Generating images ..."
python "$ROOT_DIR/scripts/generate_images.py"

echo "Rebuilding menu ..."
python "$ROOT_DIR/scripts/rebuild_menu.py"

echo "Done. Recipes are in $ROOT_DIR/recipes"
