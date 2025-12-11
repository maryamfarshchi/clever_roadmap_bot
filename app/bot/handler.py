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


ADMIN_CHAT_ID = 341781615  # چت‌آیدی تو برای گزارش ESC


# =================================================================
#   پردازش UPDATE (Message + Callback)
# =================================================================
def process_update(update):
    try:
        # ----------------------------------------------------
        #  اگر CallbackQuery بود
        # ----------------------------------------------------
        if "callback_query" in update:
            return process_callback(update["callback_query"])

        # ----------------------------------------------------
        #  اگر Message نیست
        # ----------------------------------------------------
        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        print("CHAT_ID =", chat_id)

        # ----------------------------------------------------
        #   پیدا کردن کاربر
        # ----------------------------------------------------
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
                "لطفاً با مدیر سیستم تماس بگیرید تا در *members sheet* اضافه شوید.",
            )

        # ----------------------------------------------------
        # خوش‌آمد (فقط یک‌بار)
        # ----------------------------------------------------
        if user.get("welcomed") != "Yes":
            mark_welcomed(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname'] or user['name']} عزیز! 👋\n"
                "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                main_keyboard(),
            )

        # ----------------------------------------------------
        #   دستور /start
        # ----------------------------------------------------
        if text == "/start":
            clear_user_state(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname']} عزیز! 🌟\n"
                "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                main_keyboard(),
            )

        # ----------------------------------------------------
        #   منوی اصلی
        # ----------------------------------------------------
        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        # ----------------------------------------------------
        # اگر متن نامعتبر بود
        # ----------------------------------------------------
        return send_message(chat_id, "❗ لطفاً از دکمه‌های منو استفاده کن.")

    except Exception as e:
        send_message(ADMIN_CHAT_ID, f"⚠ خطای بات:\n{str(e)}")
        print("PROCESS_UPDATE ERROR:", e)
        return


# =================================================================
# پردازش Callback (DONE / NOT_DONE)
# =================================================================
def process_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    data = cb.get("data", "")

    user = find_member(chat_id)
    team = user["team"] if user else ""

    if data.startswith("DONE::"):
        title = data.replace("DONE::", "")
        ok = False
        if team:
            ok = update_task_status(title, team, "done")

        if ok:
            return send_message(chat_id, f"🎉 عالی! «{title}» تحویل شد ✔️")
        else:
            return send_message(
                chat_id,
                f"⚠ نتونستم تسک «{title}» رو در شیت پیدا کنم، "
                "ولی یادم می‌مونه که گفتی انجام شده.",
            )

    if data.startswith("NOT_DONE::"):
        title = data.replace("NOT_DONE::", "")
        return send_message(
            chat_id,
            f"🔔 اوکی! «{title}» هنوز انجام نشده. بعداً دوباره یادت می‌ندازم.",
        )

    return send_message(chat_id, "❗ داده‌ی دکمه نامعتبر است.")


# =================================================================
#   ارسال کارهای امروز (لیست ساده)
# =================================================================
def send_today(chat_id, user):
    team = user["team"]
    tasks = get_tasks_today(team)

    if not tasks:
        return send_message(chat_id, "🌤️ امروز هیچ کاری ثبت نشده.")

    for t in tasks:
        title = t["title"]
        date_fa = t["date_fa"]
        text = (
            f"📌 *تسک امروز تیم {team}*\n"
            f"📅 {date_fa}\n"
            f"✏️ *{title}*\n"
        )
        send_message(chat_id, text)


# =================================================================
#   ارسال کارهای هفته + پیام رندوم WEEK
# =================================================================
def send_week(chat_id, user):
    team = user["team"]
    tasks = get_tasks_week(team)

    if not tasks:
        return send_message(chat_id, "📆 برای این هفته کاری ثبت نیست.")

    header = get_random_message("WEEK", TEAM=team)
    send_message(chat_id, header + "\n")

    for t in tasks:
        text = (
            f"👥 *{team}*\n"
            f"📅 {t['date_fa']}\n"
            f"✏️ {t['title']}\n"
        )
        send_message(chat_id, text)


# =================================================================
#   ارسال Pending + پیام‌های PRE2/DUE/OVR/ESC
# =================================================================
def send_pending(chat_id, user):
    team = user["team"]
    tasks = get_tasks_pending(team)

    if not tasks:
        return send_message(chat_id, "🎉 همه کارها انجام شده! عالیه 👌")

    for t in tasks:
        title = t["title"]
        date_fa = t["date_fa"]
        delay = t["delay_days"]

        if delay is None:
            continue

        # ------- تعیین نوع پیام بر اساس delay -------
        # delay = today - deadline
        #  -2 → دو روز مانده → PRE2
        #   0 → امروز → DUE
        #  1..5 → OVR
        #  >5 → ESC
        if delay > 5:
            msg_type = "ESC"
        elif delay > 0:
            msg_type = "OVR"
        elif delay == 0:
            msg_type = "DUE"
        elif delay == -2:
            msg_type = "PRE2"
        else:
            # خارج از بازه‌ی ریمایندرهای ما
            continue

        days_abs = abs(delay)

        funny = get_random_message(
            msg_type,
            NAME=user["customname"],
            TEAM=team,
            TITLE=title,
            DAYS=days_abs,
            DATE_FA=date_fa,
        )

        base_text = (
            f"📌 *تسک تیم {team}*\n"
            f"📅 {date_fa}\n"
            f"✏️ *{title}*\n\n"
            f"{funny}"
        )

        # پیام ESC علاوه بر کاربر برای مدیر هم ارسال می‌شود
        if msg_type == "ESC":
            send_message(ADMIN_CHAT_ID, f"⚠ ESCALATION\n{funny}")
            # برای خود کاربر هم ارسال می‌کنیم (بدون دکمه)
            send_message(chat_id, base_text)
            continue

        # PRE2 → فقط هشدار، بدون دکمه
        if msg_type == "PRE2":
            send_message(chat_id, base_text)
            continue

        # DUE و OVR → همراه دکمه
        buttons = [
            [
                {
                    "text": "✔️ بله تحویل دادم",
                    "callback_data": f"DONE::{title}",
                },
                {
                    "text": "❌ نه هنوز تحویل ندادم",
                    "callback_data": f"NOT_DONE::{title}",
                },
            ]
        ]
        send_buttons(chat_id, base_text, buttons)
