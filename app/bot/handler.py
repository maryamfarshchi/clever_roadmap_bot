# app/bot/handler.py
# -*- coding: utf-8 -*-

from cachetools import TTLCache

from bot.helpers import send_message, send_buttons, send_reply_keyboard
from bot.keyboards import main_keyboard, team_inline_keyboard

from core.members import find_member, save_or_add_member, set_member_welcomed
from core.tasks import get_tasks_today, get_tasks_week, get_tasks_not_done, update_task_status
from core.messages import get_welcome_message

# ✅ اگر تلگرام/رندر update را دوباره فرستاد، دوباره پردازش نشود
processed_updates = TTLCache(maxsize=20000, ttl=600)  # 10 دقیقه


def _is_start_command(text: str) -> bool:
    """
    /start
    /START
    /start@YourBot
    /start payload
    """
    t = (text or "").strip()
    if not t:
        return False
    first = t.split()[0].strip().lower()
    # remove @botusername if exists
    if "@" in first:
        first = first.split("@", 1)[0]
    return first == "/start"


def _task_text(t, show_delay=False) -> str:
    title = (t.get("title") or "").strip() or "بدون عنوان"
    date_fa = (t.get("date_fa") or "").strip()
    time = (t.get("time") or "").strip()
    ctype = (t.get("type") or "").strip()
    comment = (t.get("comment") or "").strip()

    lines = [f"<b>{title}</b>"]
    if date_fa:
        if time:
            lines.append(f"📅 {date_fa}  ⏰ {time}")
        else:
            lines.append(f"📅 {date_fa}")
    else:
        if time:
            lines.append(f"⏰ {time}")

    if show_delay and int(t.get("delay_days") or 0) > 0:
        lines.append(f"⏰ <b>{t['delay_days']} روز تاخیر</b>")

    if ctype:
        lines.append(f"📝 <b>سبک محتوا:</b> {ctype}")

    if comment:
        lines.append(f"💬 <b>توضیحات بیشتر:</b> {comment}")

    return "\n".join(lines)


async def send_daily(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        await send_buttons(chat_id, "اول تیم‌تو انتخاب کن:", team_inline_keyboard())
        return

    tasks = await get_tasks_today(member["team"])
    if not tasks:
        await send_message(chat_id, "✅ امروز تسکی نداری")
        return

    await send_message(chat_id, f"🌅 <b>کارهای امروز ({len(tasks)}):</b>")
    for t in tasks:
        buttons = [
            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
            [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
        ]
        await send_buttons(chat_id, _task_text(t), buttons)


async def send_week(chat_id):
    """
    طبق خواسته تو: دکمه نمی‌خوای، یک پیام کامل می‌خوای (نه چند پیام).
    لیست ۷ روز آینده.
    """
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        await send_buttons(chat_id, "اول تیم‌تو انتخاب کن:", team_inline_keyboard())
        return

    tasks = await get_tasks_week(member["team"])
    if not tasks:
        await send_message(chat_id, "برای ۷ روز آینده تسکی نداری 👌")
        return

    # یک پیام کامل
    msg_lines = [f"📅 <b>کارهای ۷ روز آینده ({len(tasks)}):</b>"]
    for t in tasks:
        title = (t.get("title") or "").strip() or "بدون عنوان"
        date_fa = (t.get("date_fa") or "").strip()
        time = (t.get("time") or "").strip()
        ctype = (t.get("type") or "").strip()

        line = f"• <b>{title}</b>"
        if date_fa and time:
            line += f"  |  📅 {date_fa}  ⏰ {time}"
        elif date_fa:
            line += f"  |  📅 {date_fa}"
        elif time:
            line += f"  |  ⏰ {time}"

        if ctype:
            line += f"  |  📝 {ctype}"

        msg_lines.append(line)

    await send_message(chat_id, "\n".join(msg_lines))


async def send_not_done(chat_id):
    member = await find_member(chat_id)
    if not member or not member.get("team"):
        await send_buttons(chat_id, "اول تیم‌تو انتخاب کن:", team_inline_keyboard())
        return

    tasks = await get_tasks_not_done(member["team"])
    if not tasks:
        await send_message(chat_id, "✅🔥 تسک انجام نشده‌ای نداری")
        return

    await send_message(chat_id, f"⚠️ <b>تسک‌های انجام نشده ({len(tasks)}):</b>")
    for t in tasks:
        buttons = [
            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
            [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
        ]
        await send_buttons(chat_id, _task_text(t, show_delay=True), buttons)


async def _show_main_menu(chat_id: int, member: dict | None):
    """
    همیشه وقتی کاربر تایپ کرد/گیر کرد، کیبورد رو دوباره نشون بده.
    """
    if not member or not member.get("team"):
        await send_buttons(chat_id, "تیم خودت رو انتخاب کن:", team_inline_keyboard())
        return
    await send_reply_keyboard(chat_id, "منوی اصلی:", main_keyboard())


async def process_update(update: dict):
    upd_id = update.get("update_id")
    if upd_id is not None:
        if upd_id in processed_updates:
            return
        processed_updates[upd_id] = True

    # Callback (دکمه‌های inline)
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]

        if data.startswith("done|"):
            task_id = data.split("|", 1)[1]
            ok = await update_task_status(task_id, "Done")
            await send_message(chat_id, "✅ ثبت شد (Done)" if ok else "❌ Task پیدا نشد")
            # بعد از تغییر وضعیت، منو رو هم نشون بده که کاربر گیر نکنه
            member = await find_member(chat_id)
            await _show_main_menu(chat_id, member)
            return

        if data.startswith("notyet|"):
            await send_message(chat_id, "باشه ⏰ (ریمایندرها ادامه دارن)")
            member = await find_member(chat_id)
            await _show_main_menu(chat_id, member)
            return

        if data.startswith("team|"):
            team = data.split("|", 1)[1]
            await save_or_add_member(chat_id, team=team)
            member = await find_member(chat_id)
            await _show_main_menu(chat_id, member)
            return

    # Message (reply keyboard)
    msg = update.get("message")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    user = msg.get("from", {})
    name = user.get("first_name", "کاربر")
    username = user.get("username", "")

    # ذخیره یا آپدیت عضو
    await save_or_add_member(chat_id, name=name, username=username)
    member = await find_member(chat_id)

    # ✅ start command (case-insensitive)
    if _is_start_command(text):
        # welcome فقط یک بار
        if member and not member.get("welcomed"):
            welcome = await get_welcome_message(member.get("customname") or name)
            await send_message(chat_id, welcome)
            await set_member_welcomed(chat_id, True)

        # منو یا انتخاب تیم
        await _show_main_menu(chat_id, member)
        return

    # دکمه‌ها
    if text == "لیست کارهای امروز":
        await send_daily(chat_id)
        return

    if text == "لیست کارهای هفته":
        await send_week(chat_id)
        return

    if text == "تسک های انجام نشده":
        await send_not_done(chat_id)
        return

    # هر متن دیگری: کیبورد را حتماً نمایش بده
    await _show_main_menu(chat_id, member)
