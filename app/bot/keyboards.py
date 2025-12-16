# app/bot/keyboards.py
import json

def main_keyboard():
    keyboard = {
        "keyboard": [
            [
                {"text": "لیست کارهای امروز"},
                {"text": "لیست کارهای هفته"}
            ],
            [
                {"text": "تسک های انجام نشده"}
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    return json.dumps(keyboard, ensure_ascii=False)

def team_select_keyboard():
    keyboard = {
        "keyboard": [
            [{"text": "Production"}],
            [{"text": "Ai Production"}],
            [{"text": "Digital"}],
            [{"text": "بازگشت ⬅️"}]
        ],
        "resize_keyboard": True
    }
    return json.dumps(keyboard, ensure_ascii=False)

def back_keyboard():
    keyboard = {
        "keyboard": [
            [{"text": "⬅️ بازگشت"}]
        ],
        "resize_keyboard": True
    }
    return json.dumps(keyboard, ensure_ascii=False)
