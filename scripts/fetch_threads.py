"""Fetch threads for a specific assistant and store messages in raw_threads/."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import requests
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw_threads"
API_KEY_ENV = "OPENAI_API_KEY"
ASSISTANT_ID_ENV = "ASSISTANT_ID"
MAX_PAGE = 100
API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
ASSISTANTS_BETA = {"OpenAI-Beta": "assistants=v2"}


def ensure_dirs() -> None:
  RAW_DIR.mkdir(parents=True, exist_ok=True)


def to_plain(obj: Any) -> Dict[str, Any]:
  if hasattr(obj, "model_dump"):
    try:
      return obj.model_dump()
    except Exception:
      pass
  if hasattr(obj, "model_dump_json"):
    try:
      return json.loads(obj.model_dump_json())
    except Exception:
      pass
  try:
    return json.loads(json.dumps(obj, default=str))
  except Exception:
    return {"raw": str(obj)}


def merge_messages(existing: List[Dict[str, Any]], fresh: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
  seen = {msg.get("id") for msg in existing}
  merged = existing[:]
  for msg in fresh:
    msg_id = msg.get("id")
    if msg_id in seen:
      continue
    merged.append(msg)
    seen.add(msg_id)
  merged.sort(key=lambda m: m.get("created_at", 0))
  return merged


def fetch_all_threads(client: OpenAI, assistant_id: str) -> List[Dict[str, Any]]:
  threads: List[Dict[str, Any]] = []
  after: str | None = None
  while True:
    try:
      resp = client.beta.threads.list(limit=MAX_PAGE, after=after)
    except TypeError:
      resp = client.beta.threads.list(limit=MAX_PAGE)
    except AttributeError:
      url = f"{API_BASE}/threads"
      params = {"limit": MAX_PAGE, "order": "desc", "assistant_id": assistant_id}
      if after:
        params["after"] = after
      r = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}", **ASSISTANTS_BETA}, params=params, timeout=30)
      if r.status_code in (401, 403):
        sys.stderr.write("Failed to list threads via HTTP: unauthorized (check OPENAI_API_KEY and key type supports Assistants v2)\n")
        raise SystemExit(1)
      if r.status_code >= 400:
        sys.stderr.write(f"Failed to list threads via HTTP: {r.status_code} {r.text}\n")
        break
      payload = r.json()
      data = payload.get("data", [])
      threads.extend(data)
      if not payload.get("has_more"):
        break
      after = payload.get("last_id")
      if not after:
        break
      continue
    data = [to_plain(t) for t in resp.data]
    threads.extend(data)
    if not getattr(resp, "has_more", False):
      break
    after = getattr(resp, "last_id", None)
    if not after:
      break
  filtered = [t for t in threads if str(t.get("assistant_id", "")).strip() == assistant_id]
  return filtered


def fetch_messages(client: OpenAI, thread_id: str) -> List[Dict[str, Any]]:
  messages: List[Dict[str, Any]] = []
  after: str | None = None
  while True:
    try:
      resp = client.beta.threads.messages.list(thread_id=thread_id, limit=MAX_PAGE, after=after, order="asc")
    except TypeError:
      resp = client.beta.threads.messages.list(thread_id=thread_id, limit=MAX_PAGE, order="asc")
    except AttributeError:
      url = f"{API_BASE}/threads/{thread_id}/messages"
      params = {"limit": MAX_PAGE, "order": "asc"}
      if after:
        params["after"] = after
      r = requests.get(url, headers={"Authorization": f"Bearer {client.api_key}", **ASSISTANTS_BETA}, params=params, timeout=30)
      if r.status_code in (401, 403):
        sys.stderr.write(f"[{thread_id}] Failed to list messages via HTTP: unauthorized\n")
        raise SystemExit(1)
      if r.status_code >= 400:
        sys.stderr.write(f"[{thread_id}] Failed to list messages via HTTP: {r.status_code} {r.text}\n")
        break
      payload = r.json()
      data = payload.get("data", [])
      messages.extend(data)
      if not payload.get("has_more"):
        break
      after = payload.get("last_id")
      if not after:
        break
      continue
    data = [to_plain(m) for m in resp.data]
    messages.extend(data)
    if not getattr(resp, "has_more", False):
      break
    after = getattr(resp, "last_id", None)
    if not after:
      break
  return messages


def save_thread(thread: Dict[str, Any], messages: List[Dict[str, Any]]) -> None:
  thread_id = thread.get("id")
  if not thread_id:
    return
  path = RAW_DIR / f"{thread_id}.json"
  existing: Dict[str, Any] = {}
  if path.exists():
    try:
      existing = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
      existing = {}
  merged_messages = merge_messages(existing.get("messages", []), messages)
  payload = {
    "thread": thread,
    "fetched_at": int(time.time()),
    "messages": merged_messages,
  }
  path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
  api_key = os.getenv(API_KEY_ENV)
  assistant_id = os.getenv(ASSISTANT_ID_ENV)
  if not api_key:
    sys.stderr.write(f"Missing {API_KEY_ENV}\n")
    return 1
  if not assistant_id:
    sys.stderr.write(f"Missing {ASSISTANT_ID_ENV}\n")
    return 1

  ensure_dirs()
  client = OpenAI(api_key=api_key)

  threads = fetch_all_threads(client, assistant_id)
  sys.stderr.write(f"Fetched {len(threads)} threads for assistant {assistant_id}\n")

  for thread in threads:
    tid = thread.get("id")
    if not tid:
      continue
    messages = fetch_messages(client, tid)
    save_thread(thread, messages)
  sys.stderr.write("Done fetching threads\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
