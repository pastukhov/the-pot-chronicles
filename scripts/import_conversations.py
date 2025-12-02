"""Parse ChatGPT export conversations.json, extract recipes, and write Markdown."""
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

ROOT = Path(__file__).resolve().parent.parent
EXPORT_FILE = ROOT / "export" / "conversations.json"
RECIPES_DIR = ROOT / "recipes"
API_KEY_ENV = "OPENAI_API_KEY"
MODEL = "gpt-4o-mini"

CLASSIFIER_PROMPT = (
  "You are a classifier. Determine if the following text contains a cooking recipe "
  "and select high-level food categories such as soup, meat, fish, vegetables, fermentation, desserts, experiments, beverages.\n"
  'Return JSON: {"is_recipe": true|false, "categories": ["soup", "meat", ...]}.\n'
  "Use lowercase categories; return empty list if uncertain."
)

EXTRACTION_PROMPT = (
  "Extract a structured cooking recipe from the text. Respond in Russian.\n"
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

MULTI_EXTRACTION_PROMPT = (
  "Extract every distinct cooking recipe from the text. Respond in Russian. Output a JSON array where each item matches:\n"
  "{\n"
  '  "title": "",\n'
  '  "ingredients": [],\n'
  '  "steps": [],\n'
  '  "time": "",\n'
  '  "temperature": "",\n'
  '  "notes": ""\n'
  "}\n"
  "Return at least one item only if there is a recipe; otherwise return an empty array []."
)

COMPLETION_PROMPT = (
  "You are improving an incomplete recipe. Using the provided text, produce a complete cooking recipe in Russian. "
  "If details are missing, infer plausible ingredients and steps consistent with the dish. "
  "Output strictly in JSON with non-empty title, at least 5 ingredients, and at least 3 steps:\n\n"
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


def validate_api_key() -> str:
  api_key = os.getenv(API_KEY_ENV, "").strip()
  if not api_key:
    sys.stderr.write("Missing OPENAI_API_KEY\n")
    raise SystemExit(1)
  return api_key


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
    idx = meta.get("source_recipe_index", 0)
    if msg_id:
      ids.add(f"{msg_id}:{idx}")
  return ids


def load_conversations() -> List[Dict[str, Any]]:
  if not EXPORT_FILE.exists():
    sys.stderr.write(f"Export file not found: {EXPORT_FILE}\n")
    return []
  try:
    return json.loads(EXPORT_FILE.read_text(encoding="utf-8"))
  except Exception as exc:
    sys.stderr.write(f"Failed to read export: {exc}\n")
    return []


def iter_messages(conv: Dict[str, Any]) -> Iterable[Tuple[str, Dict[str, Any]]]:
  conv_id = str(conv.get("id") or conv.get("conversation_id") or "")
  mapping = conv.get("mapping") or {}
  nodes = list(mapping.values())
  nodes.sort(key=lambda n: n.get("create_time") or 0)
  for node in nodes:
    msg = node.get("message") or {}
    msg_id = str(msg.get("id") or "")
    if not msg_id:
      continue
    yield conv_id, msg


def message_text(msg: Dict[str, Any]) -> Tuple[str, float]:
  content = msg.get("content") or {}
  text_parts: List[str] = []
  parts = content.get("parts") or []
  for part in parts:
    if isinstance(part, str):
      text_parts.append(part)
    elif isinstance(part, dict) and "text" in part:
      text_parts.append(str(part.get("text", "")))
  text = "\n".join(text_parts).strip()
  created = msg.get("create_time") or 0
  return text, created


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


def extract_structures(client: OpenAI, text: str) -> List[Dict[str, Any]]:
  resp = client.chat.completions.create(
    model=MODEL,
    max_tokens=1200,
    messages=[
      {"role": "system", "content": MULTI_EXTRACTION_PROMPT},
      {"role": "user", "content": text[:6000]},
    ],
  )
  content = resp.choices[0].message.content
  try:
    data = json.loads(content)
    if isinstance(data, dict):
      return [data]
    if isinstance(data, list):
      return data
    return []
  except Exception:
    return []


def complete_structure(client: OpenAI, text: str) -> Dict[str, Any]:
  resp = client.chat.completions.create(
    model=MODEL,
    max_tokens=700,
    messages=[
      {"role": "system", "content": COMPLETION_PROMPT},
      {"role": "user", "content": text[:6000]},
    ],
  )
  try:
    return json.loads(resp.choices[0].message.content)
  except Exception:
    return {}


def is_complete(structured: Dict[str, Any]) -> bool:
  if not structured:
    return False
  title = (structured.get("title") or "").strip()
  ings = structured.get("ingredients") or []
  steps = structured.get("steps") or []
  return bool(title) and len(ings) >= 2 and len(steps) >= 2


def build_path(title: str, created: datetime, suffix: int | None = None) -> Path:
  slug = slugify(title) or "recipe"
  if suffix is not None and suffix > 0:
    slug = f"{slug}-{suffix}"
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
  api_key = validate_api_key()
  ensure_dirs()
  conversations = load_conversations()
  if not conversations:
    sys.stderr.write("No conversations loaded; nothing to do.\n")
    return 0

  client = OpenAI(api_key=api_key)
  seen_ids = existing_message_ids()
  written = 0
  scanned = 0

  sys.stderr.write(f"Conversations loaded: {len(conversations)}\n")

  for conv in conversations:
    conv_id = str(conv.get("id") or conv.get("conversation_id") or "")
    conv_created = conv.get("create_time") or 0
    for conv_id, msg in iter_messages(conv):
      msg_id = str(msg.get("id") or "")
      if not msg_id or msg_id in seen_ids:
        continue
      text, created_ts = message_text(msg)
      if not text:
        continue
      if not created_ts:
        created_ts = conv_created or 0
      scanned += 1
      try:
        is_recipe, categories = classify(client, text)
      except Exception as exc:
        sys.stderr.write(f"[{msg_id}] classification error: {exc}\n")
        continue
      if not is_recipe:
        continue
      try:
        recipes = extract_structures(client, text)
      except Exception as exc:
        sys.stderr.write(f"[{msg_id}] extraction error: {exc}\n")
        continue
      if not recipes:
        sys.stderr.write(f"[{msg_id}] no recipes found in message\n")
        continue

      for idx, structured in enumerate(recipes):
        key = f"{msg_id}:{idx}"
        if key in seen_ids:
          continue
        if not is_complete(structured):
          filled = complete_structure(client, text)
          if is_complete(filled):
            structured = filled
          else:
            sys.stderr.write(f"[{msg_id}:{idx}] skipped: incomplete recipe after completion\n")
            continue

        title = structured.get("title") or "Без названия"
        try:
          created_dt = datetime.fromtimestamp(float(created_ts), tz=timezone.utc)
        except Exception:
          created_dt = datetime.fromtimestamp(0, tz=timezone.utc)

        path = build_path(title, created_dt, suffix=idx if idx > 0 else None)
        if path.exists():
          seen_ids.add(key)
          continue

        payload = {
          "title": title,
          "date": created_dt.isoformat(),
          "tags": ["recipe"] + categories,
          "categories": categories,
          "source_thread": conv_id,
          "source_message_id": msg_id,
          "source_recipe_index": idx,
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
          sys.stderr.write(f"[{msg_id}:{idx}] failed to write recipe: {exc}\n")
          continue
        seen_ids.add(key)
        written += 1
        sys.stderr.write(f"[{msg_id}:{idx}] recipe saved to {path}\n")

  sys.stderr.write(f"Messages scanned: {scanned}\n")
  sys.stderr.write(f"Recipes written: {written}\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
