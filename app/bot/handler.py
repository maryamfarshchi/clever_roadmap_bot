# app/bot/handler.py
# -*- coding: utf-8 -*-

from bot.keyboards import main_keyboard
from bot.helpers import send_message, send_buttons
from core.members import find_member, add_member_if_not_exists, mark_welcomed
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_pending, update_task_status
from core.messages import get_random_message
from core.state import clear_user_state

ADMIN_CHAT_ID = 341781615


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
            return send_message(chat_id, "شما ثبت نشده‌اید. با ادمین تماس بگیرید.")

        if user.get("welcomed") != "Yes":
            mark_welcomed(chat_id)
            return send_message(chat_id, f"سلام {user.get('customname') or user.get('name')} 👋", main_keyboard())

        if text == "/start":
            clear_user_state(chat_id)
            return send_message(chat_id, "از منوی زیر انتخاب کن 👇", main_keyboard())

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


def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    if data.startswith("DONE::"):
        task_id = data.replace("DONE::", "")
        if update_task_status(task_id, "Yes"):
            send_message(chat_id, "✔️ تسک انجام شد")
        else:
            send_message(chat_id, "❌ خطا در آپدیت تسک")
        return

    if data.startswith("NOT_YET::"):
        task_id = data.replace("NOT_YET::", "")
        update_task_status(task_id, "")
        send_message(chat_id, "⏳ هنوز انجام نشده")
        return

    send_message(chat_id, "دکمه نامعتبر")


def send_today(chat_id, user):
    tasks = get_tasks_today(user["team"])
    if not tasks:
        return send_message(chat_id, "امروز تسکی نداری")

    for t in tasks:
        send_message(chat_id, f"📌 *{t['title']}*\n📅 {t['date_fa']}")


def send_week(chat_id, user):
    tasks = get_tasks_week(user["team"])
    if not tasks:
        return send_message(chat_id, "این هفته تسکی نیست")

    send_message(chat_id, get_random_message("WEEK", TEAM=user["team"]))

    for t in tasks:
        send_message(chat_id, f"📅 {t['date_fa']}\n✏️ {t['title']}")


def send_pending(chat_id, user):
    tasks = get_tasks_pending(user["team"])

    if not tasks:
        return send_message(chat_id, "🎉 همه تسک‌ها انجام شدن! عالیه")

    # اول عقب‌افتاده‌ها
    tasks.sort(key=lambda t: -t["delay_days"])

    for t in tasks:
        delay = t["delay_days"]

        if delay is None:
            continue

        # فقط تسک‌های دورتر از ۲ روز آینده رو حذف کن
        if delay < -2:
            continue

        # نوع پیام
        if delay > 5:
            msg_type = "ESC"
        elif delay > 0:
            msg_type = "OVR"
        elif delay <= 0 and delay >= -2:
            msg_type = "DUE" if delay <= 0 else "PRE2"
            msg_type = "PRE2" if delay == -2 else "DUE"

        text = f"📌 *{t['title']}*\n📅 {t['date_fa']}\n\n" + get_random_message(
            msg_type,
            NAME=user.get("customname") or user.get("name"),
            TEAM=user["team"],
            TITLE=t['title'],
            DAYS=abs(delay),
            DATE_FA=t['date_fa'],
        )

        if msg_type == "ESC":
            send_message(ADMIN_CHAT_ID, f"⚠ ESCALATED\n{text}")
            send_message(chat_id, text)
            continue

        if msg_type == "PRE2":
            send_message(chat_id, text)
            continue

        buttons = [
            [
                {"text": "✔️ تحویل شد", "callback_data": f"DONE::{t['task_id']}"},
                {"text": "❌ هنوز نه", "callback_data": f"NOT_YET::{t['task_id']}"},
            ]
        ]
        send_buttons(chat_id, text, buttons)
