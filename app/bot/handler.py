# app/bot/handler.py
# -*- coding: utf-8 -*-

from bot.keyboards import main_keyboard
from bot.helpers import send_message, send_buttons

from core.members import (
    find_member,
    add_member_if_not_exists,
    mark_welcomed,
)

from core.tasks import (
    get_tasks_today,
    get_tasks_week,
    get_tasks_pending,
    update_task_status,
)

from core.messages import get_random_message
from core.state import clear_user_state


ADMIN_CHAT_ID = 341781615


# =========================================================
# UPDATE
# =========================================================
def process_update(update):
    try:
        if "callback_query" in update:
            return process_callback(update["callback_query"])

        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        user = find_member(chat_id)

        if not user:
            add_member_if_not_exists(
                chat_id=chat_id,
                name=chat.get("first_name", ""),
                username=chat.get("username", ""),
            )
            return send_message(
                chat_id,
                "👋 شما ثبت نشده‌اید.\nبا مدیر سیستم تماس بگیرید.",
            )

        if user.get("welcomed") != "Yes":
            mark_welcomed(chat_id)
            return send_message(
                chat_id,
                f"سلام {user.get('customname') or user.get('name')} 👋",
                main_keyboard(),
            )

        if text == "/start":
            clear_user_state(chat_id)
            return send_message(
                chat_id,
                "از منوی زیر انتخاب کن 👇",
                main_keyboard(),
            )

        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        return send_message(chat_id, "❗ فقط از دکمه‌ها استفاده کن.")

    except Exception as e:
        send_message(ADMIN_CHAT_ID, f"⚠ ERROR:\n{e}")
        print("HANDLER ERROR:", e)


# =========================================================
# CALLBACK
# =========================================================
def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("DONE::"):
        task_id = data.replace("DONE::", "")
        if update_task_status(task_id, "Yes"):
            return send_message(chat_id, "✔️ انجام شد و ثبت گردید.")
        return send_message(chat_id, "❌ TaskID پیدا نشد")

    if data.startswith("NOT_YET::"):
        task_id = data.replace("NOT_YET::", "")
        update_task_status(task_id, "")
        return send_message(chat_id, "⏳ هنوز انجام نشده – یادآوری ادامه دارد.")

    send_message(chat_id, "❗ callback نامعتبر")


# =========================================================
# TODAY
# =========================================================
def send_today(chat_id, user):
    tasks = get_tasks_today(user["team"])

    if not tasks:
        return send_message(chat_id, "🌤️ امروز کاری ثبت نشده")

    for t in tasks:
        send_message(
            chat_id,
            f"📌 *{t['title']}*\n📅 {t['date_fa']}",
        )


# =========================================================
# WEEK
# =========================================================
def send_week(chat_id, user):
    tasks = get_tasks_week(user["team"])

    if not tasks:
        return send_message(chat_id, "📆 کاری برای این هفته نیست")

    send_message(
        chat_id,
        get_random_message("WEEK", TEAM=user["team"]),
    )

    for t in tasks:
        send_message(
            chat_id,
            f"📅 {t['date_fa']}\n✏️ {t['title']}",
        )


# =========================================================
# PENDING – اصلاح‌شده کامل
# =========================================================
def send_pending(chat_id, user):
    tasks = get_tasks_pending(user["team"])

    if not tasks:
        return send_message(chat_id, "🎉 همه تسک‌ها انجام شده – عالیه! 👏")

    send_message(chat_id, f"📋 شما {len(tasks)} تسک انجام‌نشده دارید:")

    for t in tasks:
        delay = t["delay_days"]

        if delay > 0:
            delay_text = f"({delay} روز تاخیر ❌)"
        elif delay == 0:
            delay_text = "(مهلت امروز ⏰)"
        else:
            delay_text = f"({abs(delay)} روز مانده ✅)"

        text = f"📌 *{t['title']}*\n📅 {t['date_fa']} {delay_text}"

        # فقط برای تسک‌های نزدیک (از ۲ روز قبل تا overdue) دکمه بگذار
        if -2 <= delay:
            buttons = [
                [
                    {"text": "✔️ تحویل شد", "callback_data": f"DONE::{t['task_id']}"},
                    {"text": "❌ هنوز نه", "callback_data": f"NOT_YET::{t['task_id']}"},
                ]
            ]
            send_buttons(chat_id, text, buttons)
        else:
            # تسک‌های آینده دور: فقط نمایش
            send_message(chat_id, text)
