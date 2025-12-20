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
    async with reminder_lock:  # جدید: lock کن تا همزمان اجرا نشه
        tasks = await load_tasks()
        today_str = datetime.now(IRAN_TZ).strftime("%Y-%m-%d")

        admins = await get_members_by_team("ALL")  # فرض بر این که تیم "ALL" برای ادمین‌ها داری؛ اگر نه، تغییر بده

        for t in tasks:
            if t["done"]:
                continue

            try:
                team_members = await get_members_by_team(t["team"])
                delay = t["delay_days"]
                reminders = t["reminders"] or {}

                # چک تکرار: اگر امروز قبلاً ارسال شده، اسکیپ کن
                sent_today = reminders.get("last_sent") == today_str
                if sent_today:
                    continue

                # برای هشدار مدیر (خارج از لوپ member، چون به همه ادمین‌ها می‌ره)
                if delay > 5 and "escalated" not in reminders and admins:
                    msg = await get_random_message("هشدار مدیر", title=t["title"], team=t["team"], date=t["date_fa"], delay=delay)
                    if t.get("type"):
                        msg += f"\n📝 <b>سبک محتوا:</b> {t['type']}"
                    if t.get("comment"):
                        msg += f"\n💬 <b>توضیحات بیشتر تسک:</b> {t['comment']}"
                    for a in admins:
                        await send_message(a["chat_id"], msg)
                    ok = await update_task_reminder(t["task_id"], "escalated", today_str)
                    if ok:
                        await update_task_reminder(t["task_id"], "last_sent", today_str)
                    log_info(f"Sent escalated reminder for {t['task_id']}, update ok: {ok}")
                    continue  # بعد از ارسال، ادامه بده تا تکرار نشه

                for u in team_members:
                    member = u
                    name = member.get("customname") or member.get("name") or "کاربر"  # اولویت customname, بعد name, بعد "کاربر"

                    if delay == -2 and "2day" not in reminders:
                        msg = await get_random_message("دو روز مونده", name=name, title=t["title"], date=t["date_fa"], time=t["time"])
                        if t.get("type"):
                            msg += f"\n📝 <b>سبک محتوا:</b> {t['type']}"
                        if t.get("comment"):
                            msg += f"\n💬 <b>توضیحات بیشتر تسک:</b> {t['comment']}"
                        await send_message(u["chat_id"], msg)
                        ok = await update_task_reminder(t["task_id"], "2day", today_str)
                        if ok:
                            await update_task_reminder(t["task_id"], "last_sent", today_str)
                        log_info(f"Sent 2day reminder for {t['task_id']}, update ok: {ok}")
                        # جدید: بعد ارسال، break کن تا برای این تسک بیشتر ادامه نده
                        break

                    if delay == 0 and "deadline" not in reminders:
                        msg = await get_random_message("روز تحویل", name=name, title=t["title"], date=t["date_fa"], time=t["time"])
                        if t.get("type"):
                            msg += f"\n📝 <b>سبک محتوا:</b> {t['type']}"
                        if t.get("comment"):
                            msg += f"\n💬 <b>توضیحات بیشتر تسک:</b> {t['comment']}"
                        buttons = [
                            [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                            [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
                        ]
                        await send_buttons(u["chat_id"], msg, buttons)
                        ok = await update_task_reminder(t["task_id"], "deadline", today_str)
                        if ok:
                            await update_task_reminder(t["task_id"], "last_sent", today_str)
                        log_info(f"Sent deadline reminder for {t['task_id']}, update ok: {ok}")
                        break

                    if 1 <= delay <= 5:
                        key = f"over_{delay}"
                        if key not in reminders:
                            msg = await get_random_message("یادآوری تاخیر", name=name, title=t["title"], date=t["date_fa"], delay=delay)
                            if t.get("type"):
                                msg += f"\n📝 <b>سبک محتوا:</b> {t['type']}"
                            if t.get("comment"):
                                msg += f"\n💬 <b>توضیحات بیشتر تسک:</b> {t['comment']}"
                            await send_message(u["chat_id"], msg)
                            ok = await update_task_reminder(t["task_id"], key, today_str)
                            if ok:
                                await update_task_reminder(t["task_id"], "last_sent", today_str)
                            log_info(f"Sent {key} reminder for {t['task_id']}, update ok: {ok}")
                            break

            except Exception as e:
                log_error(f"Reminder error task={t.get('task_id')}: {e}")
