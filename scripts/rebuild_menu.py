#!/usr/bin/env python3
"""Rebuild Hugo menu and generate a static archives page."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import frontmatter
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "site/config.yaml"
RECIPES_DIR = ROOT / "recipes"
STATIC_ARCHIVES = ROOT / "site/static/archives/index.html"


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


def build_archives_html() -> str:
  items = []
  for md_file in RECIPES_DIR.rglob("*.md"):
    try:
      post = frontmatter.load(md_file)
      title = post.get("title") or md_file.stem
      date_raw = post.get("date") or md_file.stat().st_mtime
      try:
        dt = datetime.fromisoformat(str(date_raw))
      except Exception:
        dt = datetime.fromtimestamp(md_file.stat().st_mtime)
      rel = md_file.relative_to(RECIPES_DIR)
      url = "/recipes/" + str(rel.with_suffix("")).replace("\\", "/") + "/"
      items.append((dt, title, url))
    except Exception as exc:
      print(f"WARNING: could not read {md_file}: {exc}")
  items.sort(key=lambda x: x[0], reverse=True)

  html = [
    "<!DOCTYPE html>",
    "<html lang=\"ru\">",
    "<head>",
    "<meta charset=\"UTF-8\">",
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
    "<title>Архив рецептов</title>",
    "</head>",
    "<body>",
    "<h1>Архив рецептов</h1>",
  ]
  current_year = None
  for dt, title, url in items:
    if dt.year != current_year:
      if current_year is not None:
        html.append("</ul>")
      current_year = dt.year
      html.append(f"<h2>{current_year}</h2><ul>")
    html.append(f"<li><a href=\"{url}\">{title}</a> — {dt.strftime('%d.%m.%Y')}</li>")
  if items:
    html.append("</ul>")
  else:
    html.append("<p>Рецептов пока нет.</p>")
  html.append("</body></html>")
  return "\n".join(html)


def write_archives_page() -> None:
  STATIC_ARCHIVES.parent.mkdir(parents=True, exist_ok=True)
  STATIC_ARCHIVES.write_text(build_archives_html(), encoding="utf-8")
  print(f"Wrote archives page to {STATIC_ARCHIVES}")


def main() -> None:
  print("Loading config.yaml...")
  config = load_config()

  print("Rebuilding menu...")
  rebuild_menu(config)

  print("Saving config.yaml...")
  save_config(config)

  print("Generating static archives page...")
  write_archives_page()
  print("Menu updated successfully.")


if __name__ == "__main__":
  main()
