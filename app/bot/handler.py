# app/bot/handler.py
# -*- coding: utf-8 -*-

from cachetools import TTLCache
from datetime import datetime
import pytz

from bot.helpers import send_message, send_buttons, send_reply_keyboard
from bot.keyboards import main_keyboard, team_inline_keyboard

from core.members import find_member, save_or_add_member, set_member_welcomed
from core.tasks import (
    get_tasks_today,
    get_tasks_week,
    get_tasks_not_done,
    update_task_status,
    update_task_reminder,
    format_task_block,
)
from core.messages import get_welcome_message

IRAN_TZ = pytz.timezone("Asia/Tehran")
processed_updates = TTLCache(maxsize=20000, ttl=600)

def _task_text(t, show_delay=False):
    return format_task_block(t, include_delay=show_delay)

def _task_buttons(task_id: str):
    return [
        [{"text": "تحویل دادم ✅", "callback_data": f"done|{task_id}"}],
        [{"text": "تحویل ندادم ⏰", "callback_data": f"notyet|{task_id}"}],
    ]

async def send_daily(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        await send_message(chat_id, "اول تیم رو انتخاب کن 🙂")
        await send_buttons(chat_id, "انتخاب تیم:", team_inline_keyboard())
        return

    tasks = await get_tasks_today(member["team"])
    if not tasks:
        await send_message(chat_id, "✅ امروز تسکی نداری")
        return

    await send_message(chat_id, f"🌅 <b>کارهای امروز ({len(tasks)}):</b>")
    for t in tasks:
        await send_buttons(chat_id, _task_text(t), _task_buttons(t["task_id"]))

async def send_week(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        await send_message(chat_id, "اول تیم رو انتخاب کن 🙂")
        await send_buttons(chat_id, "انتخاب تیم:", team_inline_keyboard())
        return

    tasks = await get_tasks_week(member["team"])  # از امروز تا ۷ روز آینده
    if not tasks:
        await send_message(chat_id, "برای ۷ روز آینده تسکی نداری 👌")
        return

    await send_message(chat_id, f"📅 <b>کارهای ۷ روز آینده ({len(tasks)}):</b>")
    for t in tasks:
        await send_message(chat_id, _task_text(t))

async def send_not_done(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        await send_message(chat_id, "اول تیم رو انتخاب کن 🙂")
        await send_buttons(chat_id, "انتخاب تیم:", team_inline_keyboard())
        return

    tasks = await get_tasks_not_done(member["team"])
    if not tasks:
        await send_message(chat_id, "✅🔥 تسک انجام نشده‌ای نداری")
        return

    await send_message(chat_id, f"⚠️ <b>تسک‌های انجام نشده ({len(tasks)}):</b>")
    for t in tasks:
        await send_buttons(chat_id, _task_text(t, show_delay=True), _task_buttons(t["task_id"]))

async def process_update(update: dict):
    upd_id = update.get("update_id")
    if upd_id is not None:
        if upd_id in processed_updates:
            return
        processed_updates[upd_id] = True

    # ---------------- callback queries ----------------
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]

        if data.startswith("done|"):
            task_id = data.split("|", 1)[1]
            ok = await update_task_status(task_id, "Done")
            if ok:
                # ثبت اینکه کاربر روی Done کلیک کرده
                now_str = datetime.now(IRAN_TZ).strftime("%Y-%m-%d %H:%M")
                await update_task_reminder(task_id, "done_clicked", now_str)
            await send_message(chat_id, "✅ ثبت شد (Done)" if ok else "❌ Task پیدا نشد")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

        if data.startswith("notyet|"):
            task_id = data.split("|", 1)[1]
            now_str = datetime.now(IRAN_TZ).strftime("%Y-%m-%d %H:%M")
            # فقط برای اینکه «بفهمیم» کاربر گفت تحویل ندادم
            await update_task_reminder(task_id, "notyet_clicked", now_str)
            await send_message(chat_id, "باشه ⏰ ثبت شد. (فعلاً تحویل ندادی)")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

        if data.startswith("team|"):
            team = data.split("|", 1)[1]
            await save_or_add_member(chat_id, team=team)
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

    # ---------------- normal messages ----------------
    msg = update.get("message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    text_l = text.lower()

    user = msg.get("from", {})
    name = user.get("first_name", "کاربر")
    username = user.get("username", "")

    # ensure member exists
    await save_or_add_member(chat_id, name=name, username=username)
    member = await find_member(chat_id)

    if text_l == "/start":
        # welcome only once
        if member and not member.get("welcomed"):
            welcome = await get_welcome_message(member.get("customname") or name)
            await send_message(chat_id, welcome)
            await set_member_welcomed(chat_id)

        if not member or not member.get("team"):
            await send_message(chat_id, "تیم خودت رو انتخاب کن:")
            await send_buttons(chat_id, "انتخاب تیم:", team_inline_keyboard())
        else:
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
        return

    if text == "لیست کارهای امروز":
        await send_daily(chat_id)
        return

    if text == "لیست کارهای هفته":
        await send_week(chat_id)
        return

    if text == "تسک های انجام نشده":
        await send_not_done(chat_id)
        return

    # fallback: show keyboard again
    if member and member.get("team"):
        await send_reply_keyboard(chat_id, "از دکمه‌ها استفاده کن 🙂", main_keyboard())
    else:
        await send_message(chat_id, "اول /start رو بزن و تیم رو انتخاب کن 🙂")
