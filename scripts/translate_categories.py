#!/usr/bin/env python3
"""
One-off helper to translate recipe categories/tags to Russian.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes"

CATEGORY_MAP: Dict[str, str] = {
  "soup": "супы",
  "soups": "супы",
  "broth": "супы",
  "meat": "мясо",
  "beef": "мясо",
  "pork": "мясо",
  "poultry": "мясо",
  "chicken": "мясо",
  "fish": "рыба",
  "seafood": "рыба",
  "vegetable": "овощи",
  "vegetables": "овощи",
  "salad": "салаты",
  "salads": "салаты",
  "side": "гарниры",
  "side dish": "гарниры",
  "sauce": "соусы",
  "sauces": "соусы",
  "dessert": "десерты",
  "desserts": "десерты",
  "baking": "выпечка",
  "bread": "выпечка",
  "fermentation": "ферментации",
  "fermented": "ферментации",
  "pickles": "ферментации",
  "beverages": "напитки",
  "beverage": "напитки",
  "drinks": "напитки",
  "drink": "напитки",
  "experiments": "эксперименты",
  "experiment": "эксперименты",
  # Russian pass-throughs
  "супы": "супы",
  "мясо": "мясо",
  "рыба": "рыба",
  "овощи": "овощи",
  "ферментации": "ферментации",
  "десерты": "десерты",
  "эксперименты": "эксперименты",
  "напитки": "напитки",
  "салаты": "салаты",
  "соусы": "соусы",
  "выпечка": "выпечка",
}


def normalize_list(items: Any) -> List[str]:
  if items is None:
    return []
  if isinstance(items, str):
    items = [items]
  normalized: List[str] = []
  for raw in items:
    key = str(raw).strip().lower()
    if not key:
      continue
    mapped = CATEGORY_MAP.get(key, key)
    if mapped not in normalized:
      normalized.append(mapped)
  return normalized


def rewrite_file(path: Path) -> bool:
  text = path.read_text(encoding="utf-8")
  if not text.startswith("---"):
    return False
  try:
    _, fm_raw, body = text.split("---", 2)
  except ValueError:
    return False
  try:
    front = yaml.safe_load(fm_raw) or {}
  except Exception:
    return False

  changed = False

  for key in ("categories", "tags"):
    values = normalize_list(front.get(key))
    if key == "tags" and "recipe" not in values:
      values.insert(0, "recipe")
    if values and values != front.get(key):
      front[key] = values
      changed = True

  if not changed:
    return False

  front_yaml = yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip()
  new_text = f"---\n{front_yaml}\n---{body}"
  path.write_text(new_text, encoding="utf-8")
  return True


def main() -> int:
  updated = 0
  total = 0
  for md in RECIPES_DIR.rglob("*.md"):
    total += 1
    try:
      if rewrite_file(md):
        updated += 1
        print(f"updated {md}")
    except Exception as exc:
      print(f"skip {md}: {exc}", file=sys.stderr)
  print(f"Processed: {total}, updated: {updated}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
