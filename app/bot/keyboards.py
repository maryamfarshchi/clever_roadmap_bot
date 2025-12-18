# app/bot/keyboards.py
# -*- coding: utf-8 -*-

def main_keyboard():
    # ReplyKeyboardMarkup expects: List[List[KeyboardButton]]
    return [
        [{"text": "لیست کارهای امروز"}, {"text": "لیست کارهای هفته"}],
        [{"text": "تسک های انجام نشده"}],
    ]

def team_selection_keyboard():
    return [
        [{"text": "Production"}],
        [{"text": "AI Production"}],
        [{"text": "Digital"}],
    ]
