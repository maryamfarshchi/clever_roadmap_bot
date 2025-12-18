# app/bot/handler.py
# -*- coding: utf-8 -*-

import json
import os
import random
from datetime import datetime
import pytz

from core.sheets import update_cell, append_row  # async
from bot.helpers import send_message, send_buttons  # async
from bot.keyboards import main_keyboard, team_selection_keyboard
from core.members import find_member, save_or_add_member
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_overdue, update_task_status
from core.messages import get_random_message, get_welcome_message
from core.logging import log_error

IRAN_TZ = pytz.timezone("Asia/Tehran")

async def send_week(chat_id, user_info=None):
    member = find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks = get_tasks_week(team)
    if not tasks:
        await send_message(chat_id, "این هفته کاری نداری! استراحت کن 😎👍")
    else:
        await send_message(chat_id, f"📅 <b>کارهای این هفته ({len(tasks)} تسک):</b>")
        for t in tasks:
            days_left = (t["deadline"] - datetime.now(IRAN_TZ).date()).days
            days_text = " (امروز)" if days_left == 0 else f" ({days_left} روز آینده)"
            msg = f"<b>{t['title']}</b>\n📅 {t['date_fa']} ⏰ {t['time'] or ''}{days_text}"
            await send_message(chat_id, msg)

async def send_pending(chat_id, user_info=None):
    member = find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks_overdue = get_tasks_overdue(team)
    if tasks_overdue:
        await send_message(chat_id, f"⚠️ <b>تسک‌های انجام نشده ({len(tasks_overdue)} تسک):</b>")
        for t in tasks_overdue:
            msg = f"<b>{t['title']}</b>\n📅 {t['date_fa']} ⏰ {t['time'] or ''} ({t['delay_days']} روز تاخیر)"
            buttons = [
                [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}]
            ]
            await send_buttons(chat_id, msg, buttons)
    else:
        await send_message(chat_id, "تسک انجام نشده‌ای نداری! فوق‌العاده‌ای 🔥✅")

async def send_daily(chat_id, user_info=None):
    member = find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks_today = get_tasks_today(team)
    if tasks_today:
        await send_message(chat_id, f"🌅 <b>کارهای امروز ({len(tasks_today)} تسک):</b>")
        for t in tasks_today:
            msg = f"<b>{t['title']}</b>\n📅 {t['date_fa']} ⏰ {t['time'] or ''}"
            buttons = [
                [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}]
            ]
            await send_buttons(chat_id, msg, buttons)
    else:
        await send_message(chat_id, "امروز کاری نداری! 👍")

async def process_update(update):
    if "message" not in update:
        if "callback_query" in update:
            cb = update["callback_query"]
            data = cb.get("data", "")
            chat_id = cb["message"]["chat"]["id"]
            if data.startswith("done|"):
                task_id = data.split("|")[1]
                if await update_task_status(task_id, "Done"):
                    await send_message(chat_id, "عالی! تسک انجام شد ✅")
                else:
                    await send_message(chat_id, "تسک پیدا نشد!")
            elif data.startswith("notyet|"):
                task_id = data.split("|")[1]
                await send_message(chat_id, "اوکی، بعداً یادآوری می‌کنم ⏰")
            elif data.startswith("team|"):
                team = data.split("|")[1]
                save_or_add_member(chat_id, team=team)
                await send_message(chat_id, f"شما به تیم {team} اضافه شدید! ✅")
                await send_buttons(chat_id, "منوی اصلی:", main_keyboard())
        return
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    user_info = message.get("from", {})
    name = user_info.get("first_name", "کاربر")
    username = user_info.get("username", "")
    save_or_add_member(chat_id, name=name, username=username)
    member = find_member(chat_id)
    customname = member.get("customname", name)
    if text == "/start":
        if not member.get("welcomed"):
            welcome_msg = get_welcome_message(customname)
            await send_message(chat_id, welcome_msg)
            await update_cell("members", member["row"], 6, "Yes")
        if not member.get("team"):
            await send_message(chat_id, "شما ثبت نشدید! مال کدوم تیم هستید؟")
            await send_buttons(chat_id, "انتخاب تیم:", team_selection_keyboard())
        else:
            await send_buttons(chat_id, "منوی اصلی:", main_keyboard())
    elif text == "لیست کارهای امروز":
        await send_daily(chat_id)
    elif text == "لیست کارهای هفته":
        await send_week(chat_id)
    elif text == "تسک های انجام نشده":
        await send_pending(chat_id)
    else:
        await send_message(chat_id, "دستور نامعتبر! از منو استفاده کنید.")
