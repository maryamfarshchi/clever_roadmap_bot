# app/bot/keyboards.py
# -*- coding: utf-8 -*-

import json

# فانکشن برای کیبورد اصلی (منوی کاربر) - ReplyKeyboardMarkup
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

# فانکشن برای کیبورد انتخاب تیم (برای ثبت کاربر جدید) - ReplyKeyboardMarkup
def team_selection_keyboard():
    keyboard = {
        "keyboard": [
            [{"text": "Production"}],
            [{"text": "AI Production"}],
            [{"text": "Digital"}],
            [{"text": "بازگشت ⬅️"}]
        ],
        "resize_keyboard": True
    }
    return json.dumps(keyboard, ensure_ascii=False)

# فانکشن برای کیبورد بازگشت - ReplyKeyboardMarkup
def back_keyboard():
    keyboard = {
        "keyboard": [
            [{"text": "⬅️ بازگشت"}]
        ],
        "resize_keyboard": True
    }
    return json.dumps(keyboard, ensure_ascii=False)
