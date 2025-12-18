# app/scheduler/job.py
# -*- coding: utf-8 -*-

from datetime import datetime
import pytz

from core.members import get_members_by_team
from core.tasks import load_tasks, update_task_reminder
from core.messages import get_random_message
from bot.helpers import send_message, send_buttons
from bot.handler import send_daily as handler_send_daily, send_week as handler_send_week
from core.logging import log_error

IRAN_TZ = pytz.timezone("Asia/Tehran")
TEAMS = ["production", "aiproduction", "digital"]

async def run_weekly_jobs():
    for team in TEAMS:
        members = await get_members_by_team(team)
        for u in members:
            try:
                await handler_send_week(u["chat_id"])
            except Exception as e:
                log_error(f"Weekly job error for {u.get('chat_id')}: {e}")

async def run_daily_jobs():
    for team in TEAMS:
        members = await get_members_by_team(team)
        for u in members:
            try:
                await handler_send_daily(u["chat_id"])
            except Exception as e:
                log_error(f"Daily job error for {u.get('chat_id')}: {e}")

async def check_reminders():
    tasks = await load_tasks()
    today_str = datetime.now(IRAN_TZ).strftime("%Y-%m-%d")
    admins = await get_members_by_team("all")  # مدیرها تیم "ALL" (در شیت با all ذخیره کن)

    for t in tasks:
        if t["done"]:
            continue

        try:
            team_members = await get_members_by_team(t["team"])
            delay = t["delay_days"]
            reminders = t["reminders"] or {}

            # 2 روز مانده
            if delay == -2 and "2day" not in reminders:
                msg = await get_random_message("دو روز مونده", title=t["title"], date=t["date_fa"], time=t["time"])
                for u in team_members:
                    await send_message(u["chat_id"], msg)
                await update_task_reminder(t["task_id"], "2day", today_str)

            # روز تحویل
            if delay == 0 and "deadline" not in reminders:
                msg = await get_random_message("روز تحویل", title=t["title"], date=t["date_fa"], time=t["time"])
                buttons = [
                    [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                    [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}],
                ]
                for u in team_members:
                    await send_buttons(u["chat_id"], msg, buttons)
                await update_task_reminder(t["task_id"], "deadline", today_str)

            # تاخیر 1 تا 5 روز
            if 1 <= delay <= 5 and delay not in reminders.get("delays", []):
                msg = await get_random_message("یادآوری تاخیر", title=t["title"], date=t["date_fa"], time=t["time"], delay=delay)
                for u in team_members:
                    await send_message(u["chat_id"], msg)
                await update_task_reminder(t["task_id"], "delays", delay)

            # بعد از 5 روز => هشدار مدیر
            if delay > 5 and "alert" not in reminders:
                msg = await get_random_message("هشدار مدیر", title=t["title"], team=t["team"], date=t["date_fa"], delay=delay)
                for a in admins:
                    await send_message(a["chat_id"], msg)
                await update_task_reminder(t["task_id"], "alert", today_str)

        except Exception as e:
            log_error(f"Reminder error for task {t.get('task_id')}: {e}")
