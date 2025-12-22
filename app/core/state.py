# app/core/state.py
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from threading import Lock

STATE_FILE = Path("app/db/states.json")
_LOCK = Lock()


def _ensure_dir():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_states():
    _ensure_dir()
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_states(states):
    _ensure_dir()
    with _LOCK:
        STATE_FILE.write_text(
            json.dumps(states, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


_states = load_states()


def get_user_state(chat_id):
    chat_id = str(chat_id)
    if chat_id not in _states:
        _states[chat_id] = {"step": "start"}
        save_states(_states)
    return _states[chat_id]


def set_user_state(chat_id, step=None, **kwargs):
    chat_id = str(chat_id)
    if chat_id not in _states:
        _states[chat_id] = {"step": "start"}
    if step:
        _states[chat_id]["step"] = step
    for key, value in kwargs.items():
        _states[chat_id][key] = value
    save_states(_states)


def clear_user_state(chat_id):
    chat_id = str(chat_id)
    _states[chat_id] = {"step": "start"}
    save_states(_states)
