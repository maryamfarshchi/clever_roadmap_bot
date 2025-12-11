import json
from pathlib import Path

STATE_FILE = Path("app/db/states.json")


def load_states():
    """Load state file into memory."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}


def save_states(states):
    """Write updated state dictionary into JSON file."""
    STATE_FILE.write_text(
        json.dumps(states, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# -------------------------
#     GLOBAL MEMORY
# -------------------------
_states = load_states()


def get_user_state(chat_id):
    """Return user state dictionary."""
    chat_id = str(chat_id)
    if chat_id not in _states:
        _states[chat_id] = {"step": "start"}
        save_states(_states)
    return _states[chat_id]


def set_user_state(chat_id, step=None, **kwargs):
    """
    Update user state.
    Example:
       set_user_state(12345, step="choose_team")
       set_user_state(12345, step="waiting_for_range", team="AI")
    """
    chat_id = str(chat_id)

    if chat_id not in _states:
        _states[chat_id] = {"step": "start"}

    if step:
        _states[chat_id]["step"] = step

    for key, value in kwargs.items():
        _states[chat_id][key] = value

    save_states(_states)


def clear_user_state(chat_id):
    """Reset user state to default."""
    chat_id = str(chat_id)
    _states[chat_id] = {"step": "start"}
    save_states(_states)
