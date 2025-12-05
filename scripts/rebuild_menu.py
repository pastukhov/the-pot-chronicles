#!/usr/bin/env python3
"""Rebuild Hugo menu and generate a static archives page without Hugo build."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
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


def read_frontmatter(path: Path) -> tuple[dict, str]:
  text = path.read_text(encoding="utf-8")
  if not text.startswith("---"):
    return {}, text
  try:
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm) or {}, body
  except Exception:
    return {}, text


def build_archives_html(base_url: str) -> str:
  items = []
  for md_file in RECIPES_DIR.rglob("*.md"):
    try:
      meta, _ = read_frontmatter(md_file)
      title = meta.get("title") or md_file.stem
      date_raw = meta.get("date") or md_file.stat().st_mtime
      try:
        dt = datetime.fromisoformat(str(date_raw))
      except Exception:
        dt = datetime.fromtimestamp(md_file.stat().st_mtime)
      rel = md_file.relative_to(RECIPES_DIR)
      url = base_url.rstrip("/") + "/recipes/" + str(rel.with_suffix("")).replace("\\", "/") + "/"
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
    "<style>",
    ":root { --bg: #0f172a; --card: #111827; --accent: #f97316; --text: #e2e8f0; --muted: #94a3b8; }",
    "body { font-family: Arial, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px 24px 24px 220px; }",
    "a { color: var(--accent); text-decoration: none; } a:hover { text-decoration: underline; }",
    ".card { max-width: 960px; margin: 0 auto; background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid rgba(148,163,184,0.2); box-shadow: 0 20px 60px rgba(0,0,0,0.4); }",
    ".sidebar { position: fixed; top: 20px; left: 20px; width: 180px; background: rgba(17,24,39,0.9); border: 1px solid rgba(148,163,184,0.2); border-radius: 14px; padding: 14px; box-shadow: 0 20px 60px rgba(0,0,0,0.4); backdrop-filter: blur(10px); }",
    ".sidebar h3 { margin: 0 0 10px; font-size: 16px; letter-spacing: -0.01em; }",
    ".sidebar nav a { display: block; color: var(--text); padding: 6px 8px; border-radius: 8px; border: 1px solid rgba(148,163,184,0.15); background: rgba(255,255,255,0.02); margin-bottom: 6px; text-decoration: none; transition: border-color 160ms ease, transform 160ms ease; }",
    ".sidebar nav a:hover { border-color: rgba(249,115,22,0.4); transform: translateY(-1px); }",
    "</style>",
    "</head>",
    "<body>",
    "<aside class=\"sidebar\">",
    "<h3>Навигация</h3>",
    "<nav>",
    f"<a href=\"{base_url}/\">Главная</a>",
    f"<a href=\"{base_url}/archives/\">По датам</a>",
    f"<a href=\"{base_url}/tags/\">Теги</a>",
    f"<a href=\"{base_url}/recipes/\">Все рецепты</a>",
    "</nav>",
    "</aside>",
    "<div class=\"card\">",
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
  html.append("</div></body></html>")
  return "\n".join(html)


def write_archives_page(base_url: str) -> None:
  STATIC_ARCHIVES.parent.mkdir(parents=True, exist_ok=True)
  STATIC_ARCHIVES.write_text(build_archives_html(base_url), encoding="utf-8")
  print(f"Wrote archives page to {STATIC_ARCHIVES}")


def main() -> None:
  print("Loading config.yaml...")
  config = load_config()

  print("Rebuilding menu...")
  rebuild_menu(config)

  print("Saving config.yaml...")
  save_config(config)

  base_url = str(config.get("baseURL", "")).rstrip("/")
  print(f"Generating static archives page with baseURL={base_url}...")
  write_archives_page(base_url)
  print("Menu updated successfully.")


if __name__ == "__main__":
  main()
