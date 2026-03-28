"""
Simple file-based conversation memory — no database needed.
Stores the last 20 turns per Telegram user ID in a JSON file.
"""

import json
from pathlib import Path
import os

HISTORY_FILE = Path(os.getenv("HISTORY_FILE", "app/storage/history.json"))
MAX_TURNS = 20


def _load() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save(data: dict):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


def get_history(sender_id: str) -> list[dict]:
    return _load().get(sender_id, [])


def save_turn(sender_id: str, user_query: str, assistant_reply: str, sender_name: str):
    data = _load()
    history = data.get(sender_id, [])
    history.append({"role": "user",      "content": f"{sender_name} asks: {user_query}"})
    history.append({"role": "assistant", "content": assistant_reply})
    data[sender_id] = history[-(MAX_TURNS * 2):]
    _save(data)


def clear_history(sender_id: str):
    data = _load()
    data.pop(sender_id, None)
    _save(data)
