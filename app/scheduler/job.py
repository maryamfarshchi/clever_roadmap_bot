# app/scheduler/job.py
# -*- coding: utf-8 -*-

from datetime import datetime
import pytz
import asyncio  # اضافه برای lock

from core.members import get_members_by_team
from core.tasks import load_tasks, update_task_reminder
from core.messages import get_random_message
from bot.helpers import send_message, send_buttons
from bot.handler import send_daily, send_week  # اضافه برای کال لیست کامل
from core.logging import log_error, log_info  # log_info اضافه برای دیباگ

IRAN_TZ = pytz.timezone("Asia/Tehran")

TEAM_NAMES = ["Production", "AI Production", "Digital"]

# جدید: lock برای جلوگیری از اجرای همزمان check_reminders و تکرار
reminder_lock = asyncio.Lock()

async def run_daily_jobs():
    for team in TEAM_NAMES:
        members = await get_members_by_team(team)
        for u in members:
            try:
                await send_daily(u["chat_id"])  # حالا لیست کامل امروز رو می‌فرسته، نه فقط یادآوری
            except Exception as e:
                log_error(f"Daily job error {u.get('chat_id')}: {e}")

async def run_weekly_jobs():
    for team in TEAM_NAMES:
        members = await get_members_by_team(team)
        for u in members:
            try:
                await send_week(u["chat_id"])  # حالا لیست کامل هفته رو می‌فرسته، نه فقط یادآوری
            except Exception as e:
                log_error(f"Weekly job error {u.get('chat_id')}: {e}")

async def check_reminders():
    async with reminder_lock:  # قفل کن تا همزمان اجرا نشه
        tasks = await load_tasks()
        today_str = datetime.now(IRAN_TZ).strftime("%Y-%m-%d")
        current_hour = datetime.now(IRAN_TZ).hour

        admins = await get_members_by_team("ALL")  # فقط کسانی که تیم "ALL" دارند

        for t in tasks:
            if t["done"]:
                continue

            try:
                team_members = await get_members_by_team(t["team"])
                delay = t["delay_days"]
                reminders = t["reminders"] or {}

                # چک تکرار سخت: اگر قبلاً برای این type فرستاده شده (نه فقط امروز)، اسکیپ کن
                reminder_type = ""
                if delay == -2:
                    reminder_type = "2day"
                elif delay == 0:
                    reminder_type = "deadline"
                elif 1 <= delay <= 5:
                    reminder_type = f"over_{delay}"
                elif delay > 5:
                    reminder_type = "escalated"

                if reminder_type in reminders:
                    continue  # اگر قبلاً فرستاده شده، اسکیپ

                sent = False
                if delay > 5 and reminder_type == "escalated" and admins and current_hour == 8:  # فقط صبح برای هشدار مدیر
                    msg = await get_random_message("هشدار مدیر", title=t["title"], date_fa=t["date_fa"] or "", days=delay, time=t["time"] or "", team=t["team"])
                    if t.get("type"):
                        msg += f"\n📝 <b>سبک محتوا:</b> {t['type']}"
                    if t.get("comment"):
                        msg += f"\n💬 <b>توضیحات بیشتر تسک:</b> {t['comment']}"
                    for a in admins:
                        await send_message(a["chat_id"], msg)
                    ok = await update_task_reminder(t["task_id"], reminder_type, today_str)
                    log_info(f"Sent escalated reminder for {t['task_id']}, update ok: {ok}")
                    sent = True
                    continue

                for u in team_members:
                    member = u
                    name = member.get("customname") or member.get("name") or "کاربر"
                    log_info(f"Using name for {u['chat_id']}: {name}")

                    if reminder_type and reminder_type not in reminders:
                        msg = await get_random_message(reminder_type.replace("over_", "یادآوری تاخیر"), name=name, title=t["title"], date_fa=t["date_fa"] or "", days=abs(delay) if delay < 0 else delay, time=t["time"] or "")
                        if t.get("type"):
                            msg += f"\n📝 <b>سبک محتوا:</b> {t['type']}"
                        if t.get("comment"):
                            msg += f"\n💬 <b>توضیحات بیشتر تسک:</b> {t['comment']}"
                        if reminder_type == "deadline":
                            buttons = [
                                [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                                [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
                            ]
                            await send_buttons(u["chat_id"], msg, buttons)
                        else:
                            await send_message(u["chat_id"], msg)
                        sent = True

                if sent:
                    ok = await update_task_reminder(t["task_id"], reminder_type, today_str)
                    if not ok:
                        log_error(f"Failed to update {reminder_type} for {t['task_id']}")
                    log_info(f"Sent {reminder_type} reminder for {t['task_id']}, update ok: {ok}")

            except Exception as e:
                log_error(f"Reminder error task={t.get('task_id')}: {e}")
