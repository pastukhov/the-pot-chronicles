#!/usr/bin/env python3
"""Rebuild Hugo menu from recipe categories."""
from __future__ import annotations

from pathlib import Path
import yaml
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "site/config.yaml"
RECIPES_DIR = ROOT / "recipes"


def load_categories() -> list[str]:
  categories: set[str] = set()
  for md_file in RECIPES_DIR.rglob("*.md"):
    try:
      post = frontmatter.load(md_file)
      cats = post.get("categories", [])
      if isinstance(cats, str):
        cats = [cats]
      for c in cats:
        if isinstance(c, str) and c.strip():
          categories.add(c.strip().lower())
    except Exception as exc:
      print(f"WARNING: could not read {md_file}: {exc}")
  if not categories:
    categories.add("разное")
  return sorted(categories)


def load_config() -> dict:
  if not CONFIG_PATH.exists():
    return {}
  with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    return yaml.safe_load(f) or {}


def save_config(config: dict) -> None:
  with open(CONFIG_PATH, "w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True, sort_keys=False)


def rebuild_menu(config: dict, categories: list[str]) -> None:
  menu_block = {"main": []}
  weight = 1
  for cat in categories:
    menu_block["main"].append(
      {"name": cat.capitalize(), "url": f"/categories/{cat}/", "weight": weight}
    )
    weight += 1
  menu_block["main"].append({"name": "Все рецепты", "url": "/recipes/", "weight": 999})
  if "menu" not in config:
    config["menu"] = {}
  config["menu"]["main"] = menu_block["main"]


def main() -> None:
  print("Scanning categories from recipes...")
  categories = load_categories()
  print("Found categories:", categories)

  print("Loading config.yaml...")
  config = load_config()

  print("Rebuilding menu...")
  rebuild_menu(config, categories)

  print("Saving config.yaml...")
  save_config(config)
  print("Menu updated successfully.")


if __name__ == "__main__":
  main()
