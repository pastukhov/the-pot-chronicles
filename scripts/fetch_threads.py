"""Fetch threads for a specific assistant (Assistants v2) and store unseen threads."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "site" / "raw_threads"
API_BASE = "https://api.openai.com/v1"
API_KEY_ENV = "OPENAI_API_KEY"
ASSISTANT_ID_ENV = "ASSISTANT_ID"
TIMEOUT = 30
HEADERS_TEMPLATE = {"OpenAI-Beta": "assistants=v2"}


def env_or_exit() -> tuple[str, str]:
  api_key = os.getenv(API_KEY_ENV, "").strip()
  if not api_key or not api_key.startswith("sk-"):
    sys.stderr.write("Invalid or missing OPENAI_API_KEY. Use a Platform API key (sk-...).\n")
    raise SystemExit(1)
  assistant_id = os.getenv(ASSISTANT_ID_ENV, "").strip()
  if not assistant_id:
    sys.stderr.write("ASSISTANT_ID environment variable missing.\n")
    raise SystemExit(1)
  return api_key, assistant_id


def ensure_dirs() -> None:
  RAW_DIR.mkdir(parents=True, exist_ok=True)


def request_json(method: str, url: str, api_key: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
  headers = {**HEADERS_TEMPLATE, "Authorization": f"Bearer {api_key}"}
  resp = requests.request(method, url, headers=headers, params=params, timeout=TIMEOUT)
  if resp.status_code in (401, 403):
    sys.stderr.write("Unauthorized: OPENAI_API_KEY is invalid or not a Platform key.\n")
    raise SystemExit(1)
  if resp.status_code >= 400:
    sys.stderr.write(f"API error {resp.status_code}: {resp.text}\n")
    raise SystemExit(1)
  return resp.json()


def list_threads(api_key: str, assistant_id: str) -> List[Dict[str, Any]]:
  threads: List[Dict[str, Any]] = []
  after: str | None = None
  while True:
    params = {"limit": 100, "assistant_id": assistant_id}
    if after:
      params["after"] = after
    url = f"{API_BASE}/threads"
    payload = request_json("GET", url, api_key, params=params)
    data = payload.get("data", [])
    threads.extend(data)
    if not payload.get("has_more"):
      break
    after = payload.get("last_id")
    if not after:
      break
  return threads


def list_messages(api_key: str, thread_id: str) -> List[Dict[str, Any]]:
  messages: List[Dict[str, Any]] = []
  after: str | None = None
  while True:
    params = {"limit": 100, "order": "asc"}
    if after:
      params["after"] = after
    url = f"{API_BASE}/threads/{thread_id}/messages"
    payload = request_json("GET", url, api_key, params=params)
    data = payload.get("data", [])
    messages.extend(data)
    if not payload.get("has_more"):
      break
    after = payload.get("last_id")
    if not after:
      break
  return messages


def save_thread(thread_id: str, messages: List[Dict[str, Any]]) -> None:
  path = RAW_DIR / f"{thread_id}.json"
  if path.exists():
    return
  payload = {
    "thread_id": thread_id,
    "messages": messages,
    "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
  }
  path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
  api_key, assistant_id = env_or_exit()
  ensure_dirs()

  threads = list_threads(api_key, assistant_id)
  discovered = len(threads)
  new_saved = 0
  skipped = 0

  for thread in threads:
    tid = str(thread.get("id") or "").strip()
    if not tid:
      continue
    path = RAW_DIR / f"{tid}.json"
    if path.exists():
      skipped += 1
      continue
    messages = list_messages(api_key, tid)
    save_thread(tid, messages)
    new_saved += 1

  sys.stderr.write(f"Threads discovered: {discovered}\n")
  sys.stderr.write(f"New threads saved: {new_saved}\n")
  sys.stderr.write(f"Existing threads skipped: {skipped}\n")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
