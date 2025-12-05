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
        "<style>body{font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:24px;}a{color:#f97316;} .card{max-width:960px;margin:0 auto;background:#111827;padding:20px;border-radius:12px;border:1px solid rgba(148,163,184,0.2);}h1,h2{margin:0 0 12px;}</style>",
        "</head>",
        "<body>",
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
