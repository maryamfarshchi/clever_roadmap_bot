# app/bot/keyboards.py
# -*- coding: utf-8 -*-

def main_keyboard():
    return [
        [{"text": "لیست کارهای امروز"}, {"text": "لیست کارهای هفته"}],
        [{"text": "تسک های انجام نشده"}],
    ]

def team_inline_keyboard():
    return [
        [{"text": "Production", "callback_data": "team|Production"}],
        [{"text": "AI Production", "callback_data": "team|AI Production"}],
        [{"text": "Digital", "callback_data": "team|Digital"}],
    ]
