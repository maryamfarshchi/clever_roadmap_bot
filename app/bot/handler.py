# app/bot/handler.py
# -*- coding: utf-8 -*-

from datetime import datetime
import pytz

from bot.helpers import send_message, send_buttons, send_reply_keyboard
from bot.keyboards import main_keyboard, team_selection_keyboard
from core.members import find_member, save_or_add_member
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_overdue, update_task_status
from core.messages import get_welcome_message
from core.logging import log_error

IRAN_TZ = pytz.timezone("Asia/Tehran")

def _pretty_task_line(t, with_days_left=False):
    s = f"<b>{t['title']}</b>\n📅 {t['date_fa']} ⏰ {t['time'] or ''}"
    if with_days_left:
        days_left = (t["deadline"] - datetime.now(IRAN_TZ).date()).days
        if days_left == 0:
            s += " (امروز)"
        elif days_left > 0:
            s += f" ({days_left} روز آینده)"
    if t.get("delay_days", 0) > 0:
        s += f" ({t['delay_days']} روز تاخیر)"
    return s

async def send_week(chat_id, user_info=None):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks = await get_tasks_week(team)
    if not tasks:
        await send_message(chat_id, "این هفته کاری نداری! 😎")
        return

    await send_message(chat_id, f"📅 <b>کارهای ۷ روز آینده ({len(tasks)} تسک):</b>")
    for t in tasks:
        await send_message(chat_id, _pretty_task_line(t, with_days_left=True))

async def send_pending(chat_id, user_info=None):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks_overdue = await get_tasks_overdue(team)
    if not tasks_overdue:
        await send_message(chat_id, "تسک انجام نشده‌ای نداری! 🔥✅")
        return

    await send_message(chat_id, f"⚠️ <b>تسک‌های انجام نشده ({len(tasks_overdue)} تسک):</b>")
    for t in tasks_overdue:
        msg = _pretty_task_line(t)
        buttons = [
            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
            [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}]
        ]
        await send_buttons(chat_id, msg, buttons)

async def send_daily(chat_id, user_info=None):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        return
    team = member["team"]
    tasks_today = await get_tasks_today(team)
    if not tasks_today:
        await send_message(chat_id, "امروز کاری نداری! 👍")
        return

    await send_message(chat_id, f"🌅 <b>کارهای امروز ({len(tasks_today)} تسک):</b>")
    for t in tasks_today:
        msg = _pretty_task_line(t)
        buttons = [
            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
            [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}]
        ]
        await send_buttons(chat_id, msg, buttons)

async def process_update(update):
    # callback
    if "message" not in update and "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]

        if data.startswith("done|"):
            task_id = data.split("|", 1)[1]
            ok = await update_task_status(task_id, "Done")
            await send_message(chat_id, "عالی! تسک انجام شد ✅" if ok else "تسک پیدا نشد! ❌")
        elif data.startswith("notyet|"):
            await send_message(chat_id, "اوکی، یادمونه ⏰")
        elif data.startswith("team|"):
            team = data.split("|", 1)[1]
            await save_or_add_member(chat_id, team=team)
            await send_message(chat_id, f"شما به تیم {team} اضافه شدید! ✅")
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())
        return

    # message
    message = update.get("message", {})
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    user_info = message.get("from", {})
    name = user_info.get("first_name", "کاربر")
    username = user_info.get("username", "")

    await save_or_add_member(chat_id, name=name, username=username)
    member = await find_member(chat_id)
    customname = (member.get("customname") or "").strip() or name

    if text == "/start":
        if not member.get("welcomed"):
            welcome_msg = get_welcome_message(customname)
            await send_message(chat_id, welcome_msg)
            # ستون welcomed در members = col 6 (بر اساس ساختار تو)
            # بهتره این هم با update_cell async انجام بشه، ولی چون save_or_add_member داریم،
            # برای سادگی همینجا می‌تونیم مستقیم تیم/ولکام رو مدیریت کنیم اگر خواستی.
        if not member.get("team"):
            await send_message(chat_id, "شما ثبت نشدید! مال کدوم تیم هستید؟")
            # تیم‌ها رو با inline buttons می‌فرستیم که callback “team|..” بخوره
            buttons = [
                [{"text": "Production", "callback_data": "team|Production"}],
                [{"text": "AI Production", "callback_data": "team|AI Production"}],
                [{"text": "Digital", "callback_data": "team|Digital"}],
            ]
            await send_buttons(chat_id, "انتخاب تیم:", buttons)
        else:
            await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())

    elif text == "لیست کارهای امروز":
        await send_daily(chat_id)
    elif text == "لیست کارهای هفته":
        await send_week(chat_id)
    elif text == "تسک های انجام نشده":
        await send_pending(chat_id)
    else:
        await send_message(chat_id, "دستور نامعتبر! از منو استفاده کنید.")
