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
#   پردازش UPDATE (Message + Callback)
# =================================================================
def process_update(update):
    try:
        # ---------------- Callback ----------------
        if "callback_query" in update:
            return process_callback(update["callback_query"])

        # ---------------- Message -----------------
        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        print("CHAT_ID =", chat_id)

        # ---------------- Member ------------------
        user = find_member(chat_id)

        if not user:
            add_member_if_not_exists(
                chat_id=chat_id,
                name=chat.get("first_name", "") or "",
                username=chat.get("username", "") or "",
            )
            return send_message(
                chat_id,
                "👋 سلام! شما در سیستم ثبت نشده‌اید.\n"
                "لطفاً با مدیر سیستم تماس بگیرید.",
            )

        # ---------------- Welcome -----------------
        if user.get("welcomed") != "Yes":
            mark_welcomed(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname'] or user['name']} عزیز! 👋\n"
                "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                main_keyboard(),
            )

        # ---------------- /start ------------------
        if text == "/start":
            clear_user_state(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname']} عزیز! 🌟",
                main_keyboard(),
            )

        # ---------------- Menu --------------------
        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        return send_message(chat_id, "❗ لطفاً از دکمه‌های منو استفاده کن.")

    except Exception as e:
        send_message(ADMIN_CHAT_ID, f"⚠ خطای بات:\n{str(e)}")
        print("PROCESS_UPDATE ERROR:", e)


# =================================================================
#   Callback handler
# =================================================================
def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("DONE::"):
        task_id = data.replace("DONE::", "")
        if update_task_status(task_id, "done"):
            send_message(chat_id, "🎉 عالی! تسک تحویل شد ✔️")
        else:
            send_message(chat_id, "⚠️ تسک پیدا نشد.")
        return

    if data.startswith("NOT_YET::"):
        task_id = data.replace("NOT_YET::", "")
        if update_task_status(task_id, "not yet"):
            send_message(chat_id, "⏳ ثبت شد. هنوز انجام نشده.")
        else:
            send_message(chat_id, "⚠️ تسک پیدا نشد.")
        return

    send_message(chat_id, "❗ داده نامعتبر.")


# =================================================================
#   Today
# =================================================================
def send_today(chat_id, user):
    team = user["team"]
    tasks = get_tasks_today(team)

    if not tasks:
        return send_message(chat_id, "🌤️ امروز هیچ کاری ثبت نشده.")

    for t in tasks:
        send_message(
            chat_id,
            f"📌 *تسک امروز تیم {team}*\n"
            f"📅 {t['date_fa']}\n"
            f"✏️ *{t['title']}*"
        )


# =================================================================
#   Week
# =================================================================
def send_week(chat_id, user):
    team = user["team"]
    tasks = get_tasks_week(team)

    if not tasks:
        return send_message(chat_id, "📆 برای این هفته کاری ثبت نیست.")

    header = get_random_message("WEEK", TEAM=team)
    send_message(chat_id, header)

    for t in tasks:
        send_message(
            chat_id,
            f"📅 {t['date_fa']}\n✏️ {t['title']}"
        )


# =================================================================
#   Pending (PRE2 / DUE / OVR / ESC)
# =================================================================
def send_pending(chat_id, user):
    team = user["team"]
    tasks = get_tasks_pending(team)

    if not tasks:
        return send_message(chat_id, "🎉 همه کارها انجام شده! 👌")

    for t in tasks:
        delay = t["delay_days"]
        if delay is None:
            continue

        # ---- type ----
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

        funny = get_random_message(
            msg_type,
            NAME=user["customname"],
            TEAM=team,
            TITLE=t["title"],
            DAYS=abs(delay),
            DATE_FA=t["date_fa"],
        )

        base_text = (
            f"📌 *تسک تیم {team}*\n"
            f"📅 {t['date_fa']}\n"
            f"✏️ *{t['title']}*\n\n"
            f"{funny}"
        )

        # ---- ESC ----
        if msg_type == "ESC":
            send_message(ADMIN_CHAT_ID, f"⚠ ESCALATION\n{funny}")
            send_message(chat_id, base_text)
            continue

        # ---- PRE2 ----
        if msg_type == "PRE2":
            send_message(chat_id, base_text)
            continue

        # ---- DUE / OVR ----
        task_id = t["task_id"]

        buttons = [
            [
                {"text": "✔️ بله تحویل دادم", "callback_data": f"DONE::{task_id}"},
                {"text": "❌ نه هنوز تحویل ندادم", "callback_data": f"NOT_YET::{task_id}"},
            ]
        ]

        send_buttons(chat_id, base_text, buttons)
