# app/bot/keyboards.py
# -*- coding: utf-8 -*-

BTN_TODAY = "لیست کارهای امروز"
BTN_WEEK = "لیست کارهای هفته"
BTN_NOT_DONE = "تسک های انجام نشده"

def main_keyboard():
    return [
        [{"text": BTN_TODAY}, {"text": BTN_WEEK}],
        [{"text": BTN_NOT_DONE}],
    ]

def team_inline_keyboard():
    return [
        [{"text": "Production", "callback_data": "team|Production"}],
        [{"text": "AI Production", "callback_data": "team|AI Production"}],
        [{"text": "Digital", "callback_data": "team|Digital"}],
        [{"text": "ALL (Admin)", "callback_data": "team|ALL"}],  # اگر خواستی مدیر هم انتخاب بشه
    ]
