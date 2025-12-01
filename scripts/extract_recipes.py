"""Extract recipes from raw_threads and write Markdown files."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml
from openai import OpenAI
from slugify import slugify

RAW_DIR = Path(__file__).resolve().parent.parent / "raw_threads"
RECIPES_DIR = Path(__file__).resolve().parent.parent / "recipes"
API_KEY_ENV = "OPENAI_API_KEY"
MODEL = "gpt-4o-mini"
CLASSIFIER_PROMPT = (
  "You are a classifier. Determine if the following text contains a cooking recipe "
  "and select high-level food categories such as soup, meat, fish, vegetables, fermentation, desserts, experiments, beverages.\n"
  'Return JSON: {"is_recipe": true|false, "categories": ["soup", "meat", ...]}.\n'
  "Use lowercase categories; return empty list if uncertain."
)
EXTRACTION_PROMPT = (
  "Extract a structured cooking recipe from the text.\n"
  "Output strictly in the following JSON format:\n\n"
  "{\n"
  '  "title": "",\n'
  '  "ingredients": [],\n'
  '  "steps": [],\n'
  '  "time": "",\n'
  '  "temperature": "",\n'
  '  "notes": ""\n'
  "}"
)


def ensure_dirs() -> None:
  RECIPES_DIR.mkdir(parents=True, exist_ok=True)


def read_front_matter(path: Path) -> Dict[str, Any]:
  text = path.read_text(encoding="utf-8")
  if not text.startswith("---"):
    return {}
  try:
    _, fm, _ = text.split("---", 2)
    return yaml.safe_load(fm) or {}
  except Exception:
    return {}


def existing_message_ids() -> set[str]:
  ids: set[str] = set()
  for path in RECIPES_DIR.glob("**/*.md"):
    meta = read_front_matter(path)
    msg_id = meta.get("source_message_id")
    if msg_id:
      ids.add(str(msg_id))
  return ids


def message_to_text(msg: Dict[str, Any]) -> str:
  content = msg.get("content", [])
  if isinstance(content, str):
    return content
  parts: List[str] = []
  for part in content:
    if isinstance(part, dict):
      if part.get("type") == "text":
        text_obj = part.get("text") or {}
        if isinstance(text_obj, dict):
          value = text_obj.get("value")
          if value:
            parts.append(str(value))
        elif isinstance(text_obj, str):
          parts.append(text_obj)
      elif "text" in part:
        parts.append(str(part.get("text", "")))
    elif isinstance(part, str):
      parts.append(part)
  return "\n".join(parts).strip()


def load_raw_messages() -> Iterable[Tuple[str, Dict[str, Any]]]:
  for path in RAW_DIR.glob("*.json"):
    try:
      data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
      continue
    thread = data.get("thread", {})
    thread_id = thread.get("id") or path.stem
    for msg in data.get("messages", []):
      yield thread_id, msg


def classify(client: OpenAI, text: str) -> Tuple[bool, List[str]]:
  truncated = text[:6000]
  resp = client.chat.completions.create(
    model=MODEL,
    max_tokens=150,
    messages=[
      {"role": "system", "content": CLASSIFIER_PROMPT},
      {"role": "user", "content": truncated},
    ],
  )
  content = resp.choices[0].message.content
  try:
    parsed = json.loads(content)
    is_recipe = bool(parsed.get("is_recipe"))
    categories = parsed.get("categories") or []
    if isinstance(categories, str):
      categories = [categories]
    categories = [str(c).strip().lower() for c in categories if str(c).strip()]
    return is_recipe, categories
  except Exception:
    answer = content.strip().lower()
    return answer.startswith("recipe"), []


def extract_structure(client: OpenAI, text: str) -> Dict[str, Any]:
  resp = client.chat.completions.create(
    model=MODEL,
    max_tokens=500,
    messages=[
      {"role": "system", "content": EXTRACTION_PROMPT},
      {"role": "user", "content": text[:6000]},
    ],
  )
  content = resp.choices[0].message.content
  try:
    return json.loads(content)
  except Exception:
    return {}


def build_path(title: str, created: datetime) -> Path:
  slug = slugify(title) or "recipe"
  return RECIPES_DIR / created.strftime("%Y/%m/%d") / f"{slug}.md"


def write_recipe(path: Path, payload: Dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  yaml_fields = {
    "title": payload.get("title"),
    "date": payload.get("date"),
    "tags": payload.get("tags"),
    "categories": payload.get("categories"),
    "source_thread": payload.get("source_thread"),
    "source_message_id": payload.get("source_message_id"),
    "image": payload.get("image"),
    "temperature": payload.get("temperature") or None,
    "time": payload.get("time") or None,
    "notes": payload.get("notes") or None,
    "ingredients": payload.get("ingredients") or None,
    "steps": payload.get("steps") or None,
  }
  yaml_fields = {k: v for k, v in yaml_fields.items() if v not in (None, [], "")}
  front_matter = yaml.safe_dump(yaml_fields, allow_unicode=True, sort_keys=False).strip()
  body = []
  if payload.get("ingredients"):
    body.append("## Ингредиенты\n" + "\n".join(f"- {ing}" for ing in payload["ingredients"]))
  if payload.get("steps"):
    body.append("## Шаги\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(payload["steps"])))
  if payload.get("notes"):
    body.append("## Примечания\n" + payload["notes"])
  content = f"---\n{front_matter}\n---\n\n" + "\n\n".join(body) + "\n"
  path.write_text(content, encoding="utf-8")


def main() -> int:
  api_key = os.getenv(API_KEY_ENV)
  if not api_key:
    sys.stderr.write(f"Missing {API_KEY_ENV}\n")
    return 1

  ensure_dirs()
  client = OpenAI(api_key=api_key)
  seen_ids = existing_message_ids()

  found = 0
  for thread_id, msg in load_raw_messages():
    msg_id = str(msg.get("id"))
    if not msg_id or msg_id in seen_ids:
      continue
    text = message_to_text(msg)
    if not text:
      continue
    try:
      is_recipe, categories = classify(client, text)
    except Exception as exc:
      sys.stderr.write(f"[{msg_id}] classification error: {exc}\n")
      continue
    if not is_recipe:
      continue
    try:
      structured = extract_structure(client, text)
    except Exception as exc:
      sys.stderr.write(f"[{msg_id}] extraction error: {exc}\n")
      continue
    title = structured.get("title") or "Без названия"
    created_at = msg.get("created_at") or int(datetime.now(tz=timezone.utc).timestamp())
    created_dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
    path = build_path(title, created_dt)
    if path.exists():
      continue
    payload = {
      "title": title,
      "date": created_dt.isoformat(),
      "tags": ["recipe"] + categories,
      "categories": categories,
      "source_thread": thread_id,
      "source_message_id": msg_id,
      "image": structured.get("image"),
      "temperature": structured.get("temperature"),
      "time": structured.get("time"),
      "notes": structured.get("notes"),
      "ingredients": structured.get("ingredients"),
      "steps": structured.get("steps"),
    }
    try:
      write_recipe(path, payload)
    except Exception as exc:
      sys.stderr.write(f"[{msg_id}] failed to write recipe: {exc}\n")
      continue
    seen_ids.add(msg_id)
    found += 1
  sys.stderr.write(f"Recipes written: {found}\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
