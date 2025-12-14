# app/bot/handler.py
# -*- coding: utf-8 -*-

from bot.keyboards import main_keyboard
from bot.helpers import send_message, send_buttons
from core.members import find_member, add_member_if_not_exists, mark_welcomed
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_pending, update_task_status
from core.messages import get_random_message
from core.state import clear_user_state

ADMIN_CHAT_ID = 341781615  # ← اگه تغییر کرد عوض کن


def process_update(update):
    try:
        # ---------- CALLBACK ----------
        if "callback_query" in update:
            return process_callback(update["callback_query"])

        # ---------- MESSAGE ----------
        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        user = find_member(chat_id)

        # کاربر جدید → ثبت موقت
        if not user:
            add_member_if_not_exists(
                chat_id=chat_id,
                name=chat.get("first_name", ""),
                username=chat.get("username", ""),
            )
            return send_message(
                chat_id,
                "شما ثبت نشده‌اید.\nلطفاً با ادمین تماس بگیرید."
            )

        # خوش‌آمدگویی اولین بار
        if user.get("welcomed") != "Yes":
            mark_welcomed(chat_id)
            return send_message(
                chat_id,
                f"سلام {user.get('customname') or user.get('name')} خوش اومدی!",
                main_keyboard(),
            )

        # دستورات
        if text == "/start":
            clear_user_state(chat_id)
            return send_message(chat_id, "منوی اصلی", main_keyboard())

        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        return send_message(chat_id, "فقط از دکمه‌های منو استفاده کن")

    except Exception as e:
        err = str(e)
        send_message(ADMIN_CHAT_ID, f"خطا در هندلر:\n{err}")
        print("HANDLER ERROR:", err)


# =========================================================
# CALLBACK → دکمه‌های تحویل شد / هنوز نه
# =========================================================
def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("DONE::"):
        task_id = data.replace("DONE::", "")
        if update_task_status(task_id, "Yes"):
            send_message(chat_id, "عالی! تسک انجام شد")
        else:
            send_message(chat_id, "مشکلی پیش اومد. تسک پیدا نشد یا خطا در ذخیره")
        return

    if data.startswith("NOT_YET::"):
        task_id = data.replace("NOT_YET::", "")
        if update_task_status(task_id, ""):
            send_message(chat_id, "اوکی، هنوز انجام نشده")
        else:
            send_message(chat_id, "مشکلی پیش اومد")
        return

    send_message(chat_id, "دکمه نامعتبر")


# =========================================================
# امروز
# =========================================================
def send_today(chat_id, user):
    tasks = get_tasks_today(user["team"])
    if not tasks:
        return send_message(chat_id, "امروز تسکی نداری")

    for t in tasks:
        send_message(
            chat_id,
            f"*{t['title']}*\n{t['date_fa']}",
        )


# =========================================================
# هفته
# =========================================================
def send_week(chat_id, user):
    tasks = get_tasks_week(user["team"])
    if not tasks:
        return send_message(chat_id, "این هفته تسکی ثبت نشده")

    send_message(chat_id, get_random_message("WEEK", TEAM=user["team"]))

    for t in tasks:
        send_message(
            chat_id,
            f"{t['date_fa']}n{t['title']}",
        )


# =========================================================
# تسک‌های انجام نشده (overdue)
# =========================================================
def send_pending(chat_id, user):
    tasks = get_tasks_pending(user["team"])

    if not tasks:
        return send_message(chat_id, "همه تسک‌ها انجام شدن!")

    for t in tasks:
        delay = t["delay_days"]

        if delay > 5:
            msg_type = "ESC"
        elif delay > 0:
            msg_type = "OVR"
        elif delay == 0:
            msg_type = "DUE"
        elif delay == -2:
            msg_type = "PRE2"
        else:
            continue  # بقیه منفی‌ها رو نمی‌فرستیم چون فیلتر کردیم

        text = (
            f"*{t['title']}*n"
            f"{t['date_fa']}n"
            + get_random_message(
                msg_type,
                NAME=user.get("customname"),
                TEAM=user["team"],
                TITLE=t["title"],
                DAYS=abs(delay),
                DATE_FA=t["date_fa"],
            )
        )

        if msg_type == "ESC":
            send_message(ADMIN_CHAT_ID, f"ESCALATED\n{text}")
            send_message(chat_id, text)
            continue

        buttons = [[
            {"text": "تحویل شد", "callback_data": f"DONE::{t['task_id']}"},
            {"text": "هنوز نه", "callback_data": f"NOT_YET::{t['task_id']}"},
        ]]

        send_buttons(chat_id, text, buttons)
