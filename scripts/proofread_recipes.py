#!/usr/bin/env python3
"""
Проверка рецептов на опечатки/ошибки и опциональное исправление через OpenAI.

По умолчанию только выводит найденные проблемы.
С флагом --apply переписывает фронтматтер/ингредиенты/шаги/примечания исправленной версией.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = ROOT / "recipes"
API_KEY_ENV = "OPENAI_API_KEY"
MODEL = "gpt-4o-mini"

PROMPT = (
  "Ты редактор кулинарных рецептов на русском. Проверь текст на опечатки, неясности и пропуски.\n"
  "Если рецепт неполный, логично дополни ингредиенты/шаги до цельного рецепта.\n"
  "Верни JSON:\n"
  "{\n"
  '  "issues": ["строка с описанием найденных проблем" ...],\n'
  '  "fixed": {\n'
  '    "title": "",\n'
  '    "ingredients": ["...", "..."],\n'
  '    "steps": ["...", "..."],\n'
  '    "notes": ""\n'
  "  }\n"
  "}\n"
  "Сохраняй смысл блюда, стиль лаконичный и практичный. Ингредиенты — список; шаги — последовательные, минимум 3."
)


def load_recipe(path: Path) -> Tuple[Dict[str, Any], str]:
  text = path.read_text(encoding="utf-8")
  if not text.startswith("---"):
    return {}, text
  try:
    _, fm_raw, body = text.split("---", 2)
  except ValueError:
    return {}, text
  front = yaml.safe_load(fm_raw) or {}
  return front, body


def build_payload(front: Dict[str, Any], body: str) -> str:
  parts: List[str] = []
  parts.append(f"Заголовок: {front.get('title','')}")
  if front.get("ingredients"):
    parts.append("Ингредиенты:\n" + "\n".join(f"- {i}" for i in front["ingredients"]))
  if front.get("steps"):
    parts.append("Шаги:\n" + "\n".join(f"{idx+1}. {s}" for idx, s in enumerate(front["steps"])))
  if front.get("notes"):
    parts.append("Примечания:\n" + str(front["notes"]))
  if not front.get("ingredients") or not front.get("steps"):
    parts.append("Текст:\n" + body.strip())
  return "\n\n".join(parts)


def validate_api_key() -> str:
  api_key = os.getenv(API_KEY_ENV, "").strip()
  if not api_key:
    sys.stderr.write("Missing OPENAI_API_KEY\n")
    raise SystemExit(1)
  return api_key


def proofread(client: OpenAI, text: str) -> Dict[str, Any]:
  resp = client.chat.completions.create(
    model=MODEL,
    max_tokens=800,
    messages=[
      {"role": "system", "content": PROMPT},
      {"role": "user", "content": text[:6000]},
    ],
  )
  try:
    return yaml.safe_load(resp.choices[0].message.content) or {}
  except Exception:
    return {}


def apply_fix(path: Path, front: Dict[str, Any], body: str, fixed: Dict[str, Any]) -> None:
  # Keep existing meta, replace editable fields
  for key in ("title", "ingredients", "steps", "notes"):
    if key in fixed and fixed[key]:
      front[key] = fixed[key]
  fm_text = yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip()
  new_body_parts: List[str] = []
  if front.get("ingredients"):
    new_body_parts.append("## Ингредиенты\n" + "\n".join(f"- {i}" for i in front["ingredients"]))
  if front.get("steps"):
    new_body_parts.append("## Шаги\n" + "\n".join(f"{idx+1}. {s}" for idx, s in enumerate(front["steps"])))
  if front.get("notes"):
    new_body_parts.append("## Примечания\n" + str(front["notes"]))
  new_text = f"---\n{fm_text}\n---\n\n" + "\n\n".join(new_body_parts) + "\n"
  path.write_text(new_text, encoding="utf-8")


def main() -> int:
  parser = argparse.ArgumentParser(description="Проверка рецептов на ошибки/опечатки")
  parser.add_argument("--apply", action="store_true", help="перезаписать рецепты исправленной версией")
  args = parser.parse_args()

  api_key = validate_api_key()
  client = OpenAI(api_key=api_key)

  total = 0
  changed = 0
  for md in sorted(RECIPES_DIR.rglob("*.md")):
    total += 1
    front, body = load_recipe(md)
    if not front:
      print(f"[skip] {md} (нет фронтматтера)")
      continue
    payload = build_payload(front, body)
    result = proofread(client, payload)
    issues = result.get("issues") or []
    fixed = result.get("fixed") or {}
    if issues:
      print(f"[issues] {md}:")
      for it in issues:
        print(f"  - {it}")
    if args.apply and fixed:
      apply_fix(md, front, body, fixed)
      changed += 1
      print(f"[fixed] {md}")

  print(f"Checked: {total}, fixed: {changed}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
