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


# =================================================================
#   پردازش UPDATE
# =================================================================
def process_update(update):
    try:
        # -------- Callback --------
        if "callback_query" in update:
            return process_callback(update["callback_query"])

        # -------- Message ---------
        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        user = find_member(chat_id)

        # -------- Register --------
        if not user:
            add_member_if_not_exists(
                chat_id=chat_id,
                name=chat.get("first_name", ""),
                username=chat.get("username", ""),
            )
            return send_message(
                chat_id,
                "👋 شما ثبت نشده‌اید.\nبا مدیر تماس بگیرید.",
            )

        # -------- Welcome ---------
        if user.get("welcomed") != "Yes":
            mark_welcomed(chat_id)
            return send_message(
                chat_id,
                f"سلام {user.get('customname') or user.get('name')} 👋",
                main_keyboard(),
            )

        # -------- Start ----------
        if text == "/start":
            clear_user_state(chat_id)
            return send_message(
                chat_id,
                f"سلام {user.get('customname')} 🌟",
                main_keyboard(),
            )

        # -------- Menu -----------
        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        return send_message(chat_id, "❗ از دکمه‌ها استفاده کن.")

    except Exception as e:
        send_message(ADMIN_CHAT_ID, f"⚠ خطا:\n{str(e)}")
        print("HANDLER ERROR:", e)


# =================================================================
#   Callback
# =================================================================
def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("DONE::"):
     update_task_status(task_id, "done")
        return send_message(chat_id, "✔️ انجام شد")

    if data.startswith("NOT_YET::"):
        task_id = data.replace("NOT_YET::", "")
        update_task_status(task_id, "not yet")
        return send_message(chat_id, "⏳ هنوز انجام نشده")

    send_message(chat_id, "❗ داده نامعتبر")


# =================================================================
#   Today
# =================================================================
def send_today(chat_id, user):
    team = (user.get("team") or "").lower()
    tasks = get_tasks_today(team)

    if not tasks:
        return send_message(chat_id, "🌤️ امروز کاری نیست.")

    for t in tasks:
        send_message(
            chat_id,
            f"📅 {t['date_fa']}\n✏️ *{t['title']}*"
        )


# =================================================================
#   Week
# =================================================================
def send_week(chat_id, user):
    team = (user.get("team") or "").lower()
    tasks = get_tasks_week(team)

    if not tasks:
        return send_message(chat_id, "📆 این هفته کاری نیست.")

    header = get_random_message("WEEK", TEAM=team)
    send_message(chat_id, header)

    for t in tasks:
        send_message(chat_id, f"📅 {t['date_fa']}\n✏️ {t['title']}")


# =================================================================
#   Pending
# =================================================================
def send_pending(chat_id, user):
    team = (user.get("team") or "").lower()
    tasks = get_tasks_pending(team)

    if not tasks:
        return send_message(chat_id, "🎉 همه انجام شده!")

    for t in tasks:
        delay = t["delay"]
        if delay is None:
            continue

        if delay > 5:
            msg_type = "ESC"
        elif delay > 0:
            msg_type = "OVR"
        elif delay == 0:
            msg_type = "DUE"
        elif delay == -2:
            msg_type = "PRE2"
        else:
            continue

        text = get_random_message(
            msg_type,
            NAME=user.get("customname"),
            TEAM=team,
            TITLE=t["title"],
            DAYS=abs(delay),
            DATE_FA=t["date_fa"],
        )

        base = f"📅 {t['date_fa']}\n✏️ *{t['title']}*\n\n{text}"

        if msg_type == "ESC":
            send_message(ADMIN_CHAT_ID, base)
            send_message(chat_id, base)
            continue

        if msg_type == "PRE2":
            send_message(chat_id, base)
            continue

task_id = t["task_id"]

buttons = [
    [
        {"text": "✔️ بله تحویل دادم", "callback_data": f"DONE::{task_id}"},
        {"text": "❌ نه هنوز تحویل ندادم", "callback_data": f"NOT_YET::{task_id}"},
    ]
]

send_buttons(chat_id, base_text, buttons)

