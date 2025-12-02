"""Generate images for recipes missing `image` front matter."""
from __future__ import annotations

import base64
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml
from openai import OpenAI
from slugify import slugify

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes"
IMAGES_DIR = ROOT / "images"
API_KEY_ENV = "OPENAI_API_KEY"
IMAGE_MODEL = "gpt-image-1"

PROMPT_TEMPLATE = (
  "Generate a food photography image of the finished dish.\n"
  "Style: minimalistic, soft natural lighting, shallow depth-of-field.\n"
  "Subject: final plated dish.\n"
  "Recipe: {title}\n"
  "Ingredients: {ingredients}"
)


def read_front_matter(path: Path) -> Tuple[Dict[str, Any], str]:
  text = path.read_text(encoding="utf-8")
  if not text.startswith("---"):
    return {}, text
  try:
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm) or {}
    return meta, body.lstrip("\n")
  except Exception:
    return {}, text


def write_front_matter(path: Path, meta: Dict[str, Any], body: str) -> None:
  clean_meta = {k: v for k, v in meta.items() if v not in ("", None, [])}
  fm = yaml.safe_dump(clean_meta, allow_unicode=True, sort_keys=False).strip()
  content = f"---\n{fm}\n---\n\n{body.lstrip()}"
  path.write_text(content, encoding="utf-8")


def parse_date(meta: Dict[str, Any], fallback: Path) -> datetime:
  raw_date = meta.get("date")
  if raw_date:
    try:
      return datetime.fromisoformat(str(raw_date))
    except Exception:
      pass
  return datetime.fromtimestamp(fallback.stat().st_mtime, tz=timezone.utc)


def build_image_path(title: str, created: datetime) -> Path:
  slug = slugify(title) or "recipe"
  return IMAGES_DIR / created.strftime("%Y/%m/%d") / f"{slug}.jpg"


def generate_image(client: OpenAI, prompt: str) -> bytes:
  resp = client.images.generate(
    model=IMAGE_MODEL,
    prompt=prompt,
    size="1024x1024",
  )
  b64_data = resp.data[0].b64_json
  return base64.b64decode(b64_data)


def main() -> int:
  api_key = os.getenv(API_KEY_ENV)
  if not api_key:
    sys.stderr.write(f"Missing {API_KEY_ENV}\n")
    return 1

  client = OpenAI(api_key=api_key)
  IMAGES_DIR.mkdir(parents=True, exist_ok=True)

  for path in RECIPES_DIR.glob("**/*.md"):
    meta, body = read_front_matter(path)
    if not meta:
      continue
    if meta.get("image"):
      img_path = Path(meta["image"].lstrip("/"))
      if (ROOT / img_path).exists():
        continue
    title = meta.get("title") or path.stem
    ingredients = meta.get("ingredients") or []
    prompt = PROMPT_TEMPLATE.format(title=title, ingredients=", ".join(ingredients))
    created_dt = parse_date(meta, path)
    image_fs_path = build_image_path(title, created_dt)
    if image_fs_path.exists():
      meta["image"] = "/" + str(image_fs_path.relative_to(ROOT)).replace("\\", "/")
      write_front_matter(path, meta, body)
      continue
    try:
      image_bytes = generate_image(client, prompt)
    except Exception as exc:
      sys.stderr.write(f"[{path}] image generation failed: {exc}\n")
      continue
    image_fs_path.parent.mkdir(parents=True, exist_ok=True)
    image_fs_path.write_bytes(image_bytes)
    meta["image"] = "/" + str(image_fs_path.relative_to(ROOT)).replace("\\", "/")
    write_front_matter(path, meta, body)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
