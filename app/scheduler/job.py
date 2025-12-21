# app/scheduler/job.py
# -*- coding: utf-8 -*-

from datetime import datetime
import pytz
import asyncio

from core.members import get_members_by_team
from core.tasks import (
    load_tasks,
    update_task_reminder,
    get_tasks_today,
    get_tasks_previous_week,
    group_tasks_by_date,
    format_task_block,
)
from core.messages import get_random_message
from bot.helpers import send_message, send_buttons
from core.logging import log_error, log_info

IRAN_TZ = pytz.timezone("Asia/Tehran")

TEAM_NAMES = ["Production", "AI Production", "Digital"]

reminder_lock = asyncio.Lock()

async def run_daily_jobs():
    """
    هر روز صبح: یک پیام کامل لیستی، بدون دکمه
    """
    for team in TEAM_NAMES:
        members = await get_members_by_team(team)
        for u in members:
            try:
                tasks = await get_tasks_today(team)
                name = u.get("customname") or u.get("name") or "رفیق"

                if not tasks:
                    await send_message(u["chat_id"], f"☀️ صبح بخیر <b>{name}</b>!\n✅ امروز تسکی نداری.")
                    continue

                blocks = [f"☀️ صبح بخیر <b>{name}</b>!\n📌 کارهای امروزت ({len(tasks)}):\n"]
                for t in tasks:
                    blocks.append(format_task_block(t))
                    blocks.append("")  # فاصله

                await send_message(u["chat_id"], "\n".join(blocks).strip())
            except Exception as e:
                log_error(f"Daily job error {u.get('chat_id')}: {e}")

async def run_weekly_jobs():
    """
    شنبه‌ها: هفته‌ی گذشته (به تفکیک روز/تاریخ) یک پیام بدون دکمه
    """
    for team in TEAM_NAMES:
        members = await get_members_by_team(team)
        for u in members:
            try:
                tasks = await get_tasks_previous_week(team)
                name = u.get("customname") or u.get("name") or "رفیق"

                if not tasks:
                    await send_message(u["chat_id"], f"📅 <b>{name}</b>\nهفته‌ی گذشته تسکی ثبت نشده بود 👌")
                    continue

                lines = [f"📅 <b>{name}</b>\n🗂️ گزارش هفته‌ی گذشته ({len(tasks)} تسک):\n"]
                for d, items in group_tasks_by_date(tasks):
                    day = items[0].get("day_fa", "")
                    date_fa = items[0].get("date_fa", "")
                    lines.append(f"🗓️ <b>{day} | {date_fa}</b>")
                    for t in items:
                        lines.append(f"• {t['title']}" + (f" ⏰ {t['time']}" if t.get("time") else ""))
                    lines.append("")

                await send_message(u["chat_id"], "\n".join(lines).strip())
            except Exception as e:
                log_error(f"Weekly job error {u.get('chat_id')}: {e}")

async def check_reminders():
    """
    ریمایندرها دوره‌ای چک می‌شوند تا اگر بعداً ساعت تسک ست شد هم تشخیص بده.
    """
    async with reminder_lock:
        tasks = await load_tasks()

        now = datetime.now(IRAN_TZ)
        today_str = now.strftime("%Y-%m-%d")
        current_hm = (now.hour, now.minute)

        # مدیرها: کسانی که team = ALL دارند (طبق کد خودت)
        admins = await get_members_by_team("ALL")

        for t in tasks:
            if t.get("done"):
                continue

            try:
                delay = int(t.get("delay_days", 0))
                reminders = t.get("reminders") or {}

                # --- تعیین نوع ریمایندر ---
                # 2 روز قبل
                if delay == -2:
                    reminder_type = "2day"
                    # فقط یکبار
                    if reminder_type in reminders:
                        continue

                # روز تحویل: اگر ساعت دارد، ریمایندر وابسته به ساعت
                elif delay == 0:
                    task_time = t.get("time") or ""
                    parsed = None
                    if task_time:
                        parsed = __import__("core.tasks", fromlist=["parse_time_hhmm"]).parse_time_hhmm(task_time)

                    # اگر ساعت دارد: فقط وقتی از زمانش رد شد (و کلید deadline_time هنوز ثبت نشده)
                    if parsed:
                        key = "deadline_time"
                        # اگر امروز فرستاده شده، ادامه نده
                        if str(reminders.get(key, "")).startswith(today_str):
                            continue
                        # فقط اگر زمان تسک رسیده
                        if current_hm < parsed:
                            continue
                        reminder_type = "deadline"
                        reminder_key = key
                    else:
                        # اگر ساعت ندارد: صبح یکبار
                        reminder_type = "deadline"
                        reminder_key = "deadline_morning"
                        if reminder_key in reminders:
                            continue

                # تاخیر 1 تا 5 روز
                elif 1 <= delay <= 5:
                    reminder_type = f"over_{delay}"
                    if reminder_type in reminders:
                        continue

                # بیشتر از 5 روز: escalation (یکبار)
                elif delay > 5:
                    reminder_type = "escalated"
                    if reminder_type in reminders:
                        continue
                else:
                    # بقیه حالات (مثلاً -1) فعلاً ریمایندر ندارد
                    continue

                # --- ارسال ---
                sent = False

                # escalation فقط به مدیرها، ترجیحاً صبح‌ها (این شرط را اگر می‌خواهی تغییر بده)
                if reminder_type == "escalated":
                    if not admins:
                        continue
                    msg = await get_random_message("escalated", **{
                        "title": t.get("title", ""),
                        "date_fa": t.get("date_fa", ""),
                        "days": delay,
                        "time": t.get("time", ""),
                        "team": t.get("team", "")
                    })
                    # اضافه کردن نوع و کامنت
                    if t.get("type"):
                        msg += f"\n🧩 <b>سبک محتوا:</b> {t['type']}"
                    if t.get("comment"):
                        msg += f"\n💬 <b>توضیحات بیشتر:</b> {t['comment']}"

                    for a in admins:
                        await send_message(a["chat_id"], msg)

                    ok = await update_task_reminder(t["task_id"], "escalated", today_str)
                    log_info(f"Sent escalated for {t['task_id']} ok={ok}")
                    continue

                # اعضای تیم مربوطه
                team_members = await get_members_by_team(t["team"])
                if not team_members:
                    # اگر عضو پیدا نشد، لاگ بزن تا سریع بفهمیم مشکل تیم‌هاست
                    log_error(f"No members found for team={t.get('team')} task={t.get('task_id')}")
                    continue

                for u in team_members:
                    name = u.get("customname") or u.get("name") or "رفیق"

                    # message type ها باید در شیت Messages وجود داشته باشند:
                    # 2day / deadline / over_1 ... over_5
                    msg = await get_random_message(reminder_type, **{
                        "name": name,
                        "title": t.get("title", ""),
                        "date_fa": t.get("date_fa", ""),
                        "days": abs(delay) if delay < 0 else delay,
                        "time": t.get("time", "")
                    })

                    if t.get("type"):
                        msg += f"\n🧩 <b>سبک محتوا:</b> {t['type']}"
                    if t.get("comment"):
                        msg += f"\n💬 <b>توضیحات بیشتر:</b> {t['comment']}"

                    # روز تحویل: اگر می‌خواهی دکمه داشته باشد، فقط برای deadline بگذار
                    if reminder_type == "deadline":
                        buttons = [
                            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                            [{"text": "تحویل ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
                        ]
                        await send_buttons(u["chat_id"], msg, buttons)
                    else:
                        await send_message(u["chat_id"], msg)

                    sent = True

                # --- ثبت در reminders برای جلوگیری از تکرار ---
                if sent:
                    if delay == 0 and (t.get("time") or ""):
                        # deadline_time
                        key = "deadline_time"
                        ok = await update_task_reminder(t["task_id"], key, f"{today_str} {t.get('time','')}")
                        log_info(f"Sent deadline_time for {t['task_id']} ok={ok}")
                    elif delay == 0:
                        ok = await update_task_reminder(t["task_id"], "deadline_morning", today_str)
                        log_info(f"Sent deadline_morning for {t['task_id']} ok={ok}")
                    else:
                        ok = await update_task_reminder(t["task_id"], reminder_type, today_str)
                        log_info(f"Sent {reminder_type} for {t['task_id']} ok={ok}")

            except Exception as e:
                log_error(f"Reminder error task={t.get('task_id')}: {e}")
