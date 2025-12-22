# app/bot/handler.py
# -*- coding: utf-8 -*-

from cachetools import TTLCache

from bot.helpers import send_message, send_buttons, send_reply_keyboard
from bot.keyboards import main_keyboard, team_inline_keyboard

from core.members import find_member, save_or_add_member, set_member_welcomed
from core.tasks import (
    get_tasks_today,
    get_tasks_week,
    get_tasks_not_done,
    update_task_status,
    update_task_reminder,   # ✅ اضافه شد
    format_task_block,
)
from core.messages import get_welcome_message

processed_updates = TTLCache(maxsize=20000, ttl=600)


def _task_text(t, show_delay=False):
    return format_task_block(t, include_delay=show_delay)


async def process_update(update: dict):
    upd_id = update.get("update_id")
    if upd_id is not None:
        if upd_id in processed_updates:
            return
        processed_updates[upd_id] = True

    # ----- CALLBACKS -----
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]

        if data.startswith("done|"):
            task_id = data.split("|", 1)[1]
            ok = await update_task_status(task_id, "Done")
            await send_message(chat_id, "✅ ثبت شد (Done)" if ok else "❌ Task پیدا نشد")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

        if data.startswith("notyet|"):
            task_id = data.split("|", 1)[1]

            # ✅ ثبت اینکه کاربر گفت "تحویل ندادم"
            # می‌تونی بعداً تو گزارش‌ها ازش استفاده کنی
            try:
                await update_task_reminder(task_id, "notyet_last", datetime_now_tehran_str())
                # شمارنده هم اضافه می‌کنیم
                # (اگر نبود، بعداً تو check_reminders از reminders می‌خونیم)
                # اینجا ساده نگه می‌داریم و فقط last رو می‌زنیم
            except Exception:
                pass

            await send_message(chat_id, "باشه ⏰ ثبت شد که هنوز تحویل ندادی.")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

        if data.startswith("team|"):
            team = data.split("|", 1)[1]
            await save_or_add_member(chat_id, team=team)
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
            return

    # ----- MESSAGES -----
    msg = update.get("message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    text_l = text.lower()

    user = msg.get("from", {})
    name = user.get("first_name", "کاربر")
    username = user.get("username", "")

    await save_or_add_member(chat_id, name=name, username=username)
    member = await find_member(chat_id)

    if text_l == "/start":
        if member and not member.get("welcomed"):
            welcome = await get_welcome_message(member.get("customname") or name)
            await send_message(chat_id, welcome)
            await set_member_welcomed(chat_id)

        member = await find_member(chat_id)
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

    if member and member.get("team"):
        await send_reply_keyboard(chat_id, "از دکمه‌ها استفاده کن 🙂", main_keyboard())
    else:
        await send_message(chat_id, "اول /start رو بزن و تیم رو انتخاب کن 🙂")


# ✅ تابع کمکی برای زمان تهران (برای ثبت notyet_last)
def datetime_now_tehran_str():
    import pytz
    from datetime import datetime
    tz = pytz.timezone("Asia/Tehran")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M")
