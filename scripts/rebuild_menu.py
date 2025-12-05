#!/usr/bin/env python3
"""Rebuild Hugo menu for archives and tags."""
from __future__ import annotations

from pathlib import Path
import yaml
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "site/config.yaml"
RECIPES_DIR = ROOT / "recipes"


def load_config() -> dict:
  if not CONFIG_PATH.exists():
    return {}
  with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    return yaml.safe_load(f) or {}


def save_config(config: dict) -> None:
  with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True, sort_keys=False)


def rebuild_menu(config: dict) -> None:
  menu_block = {
    "main": [
      {"name": "По датам", "url": "/archives/", "weight": 1},
      {"name": "Теги", "url": "/tags/", "weight": 2},
      {"name": "Все рецепты", "url": "/recipes/", "weight": 999},
    ]
  }
  config.setdefault("menu", {})
  config["menu"]["main"] = menu_block["main"]


def main() -> None:
  print("Loading config.yaml...")
  config = load_config()

  print("Rebuilding menu...")
  rebuild_menu(config)

  print("Saving config.yaml...")
  save_config(config)
  print("Menu updated successfully.")


if __name__ == "__main__":
  main()
