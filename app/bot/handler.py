# app/bot/handler.py

from bot.keyboards import main_keyboard
from bot.helpers import send_message
from core.members import find_member, add_member_if_not_exists
from core.tasks import get_tasks_for
from core.messages import get_random_message
from core.state import get_user_state, set_user_state, clear_user_state

# ============================================================
#  پردازش اصلی آپدیت‌های دریافتی از تلگرام
# ============================================================
def process_update(update):

    try:
        # آپدیت نامعتبر؟
        if "message" not in update:
            return

        msg = update["message"]
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = msg.get("text", "").strip()

        if not chat_id:
            return

        # ============================
        # پیدا کردن یا ساخت کاربر
        # ============================
        user = find_member(chat_id)

        if not user:
            # ساخت کاربر جدید در members
            add_member_if_not_exists(
                chat_id=chat_id,
                name=chat.get("first_name", ""),
                username=chat.get("username", "")
            )

            send_message(
                chat_id,
                "👋 سلام! الان به سیستم اضافه شدی.\n"
                "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                main_keyboard()
            )
            return

        # ============================
        # خواندن state کاربر
        # ============================
        state = get_user_state(chat_id)

        # ============================
        # فرمان /start
        # ============================
        if text == "/start":
            clear_user_state(chat_id)
            return send_message(
                chat_id,
                f"سلام {user['customname']} عزیز! 🌟\n"
                "از منوی زیر یکی از گزینه‌ها را انتخاب کن:",
                main_keyboard()
            )

        # ============================
        # منوی اصلی
        # ============================
        if text == "لیست کارهای امروز":
            return send_today(chat_id, user)

        if text == "لیست کارهای هفته":
            return send_week(chat_id, user)

        if text == "تسک های انجام نشده":
            return send_pending(chat_id, user)

        # ============================
        # هیچ گزینه مطابق نبود → پیام پیش‌فرض
        # ============================
        send_message(chat_id, "❗ لطفاً از دکمه‌های منو استفاده کن.")
        return

    except Exception as e:
        # خطای رندر، شیت، تایم، هر چی → لاگ نشود فقط امنیت
        send_message(341781615, f"⚠ خطای بات:\n{str(e)}")
        return



# ============================================================
#  ارسال «کارهای امروز»
# ============================================================
def send_today(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="today")

    if not tasks:
        return send_message(chat_id, "🌤️ امروز هیچ کاری ثبت نشده.")

    text = f"📅 *کارهای امروز ({team})*\n\n"

    for t in tasks:
        line = f"🔹 *{t['title']}* ({t['type']})\n"
        if t.get('time'):
            line += f"⏰ ساعت: {t['time']}\n"
        if t.get('comment'):
            line += f"💬 توضیح: {t['comment']}\n"
        text += line + "\n"

    send_message(chat_id, text)



# ============================================================
#  ارسال «کارهای هفته»
# ============================================================
def send_week(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="week")

    if not tasks:
        return send_message(chat_id, "📆 برای این هفته کاری ثبت نیست.")

    text = f"📆 *لیست کارهای هفته ({team})*\n\n"

    for t in tasks:
        line = f"🔸 *{t['title']}* ({t['type']})\n"
        line += f"📅 تاریخ: {t['date']}\n"
        if t.get('time'):
            line += f"⏰ {t['time']}\n"
        text += line + "\n"

    send_message(chat_id, text)



# ============================================================
#  ارسال «تسک‌های انجام نشده»
# ============================================================
def send_pending(chat_id, user):
    team = user["team"]
    tasks = get_tasks_for(team, mode="pending")

    if not tasks:
        return send_message(chat_id, "🎉 همه کارها انجام شده! عالیه 👌")

    text = f"⚠ *کارهای انجام‌نشده ({team})*\n\n"

    for t in tasks:
        message = get_random_message(
            "DUE",
            NAME=user["customname"],
            TEAM=user["team"],
            TITLE=t.get("title", "")
        )
        text += message + "\n\n"

    send_message(chat_id, text)
