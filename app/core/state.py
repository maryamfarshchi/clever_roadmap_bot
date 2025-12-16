# app/core/state.py
import json
from pathlib import Path

STATE_FILE = Path("app/db/states.json")

def load_states():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def save_states(states):
    STATE_FILE.write_text(json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8")

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
