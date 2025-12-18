# app/scheduler/job.py
# -*- coding: utf-8 -*-

from datetime import datetime
import pytz

from core.members import get_members_by_team
from core.tasks import _load_tasks, get_tasks_nearing_deadline, get_tasks_deadline_today, get_tasks_delayed, update_task_reminder
from core.messages import get_random_message
from bot.handler import send_message, send_buttons  # async
from bot.handler import send_daily as handler_send_daily, send_week as handler_send_week
from core.logging import log_error, log_info

TEAMS = ["production", "aiproduction", "digital"]

IRAN_TZ = pytz.timezone("Asia/Tehran")

async def run_weekly_jobs():
    for team in TEAMS:
        members = get_members_by_team(team)
        for user in members:
            try:
                await handler_send_week(user["chat_id"], user)
            except Exception as e:
                log_error(f"Weekly job error for user {user['chat_id']}: {e}")

async def run_daily_jobs():
    for team in TEAMS:
        members = get_members_by_team(team)
        for user in members:
            try:
                await handler_send_daily(user["chat_id"], user)
            except Exception as e:
                log_error(f"Daily job error for user {user['chat_id']}: {e}")

async def check_reminders():
    tasks = _load_tasks()
    today_str = datetime.now(IRAN_TZ).strftime("%Y-%m-%d")
    admins = get_members_by_team("ALL") or []

    for t in tasks:
        if t["done"]:
            continue

        team_members = get_members_by_team(t["team"]) or []
        delay = t["delay_days"]

        try:
            if delay == -2 and '2day' not in t["reminders"]:
                msg = get_random_message("دو روز مونده", title=t["title"], date=t["date_fa"], time=t["time"])
                for user in team_members:
                    await send_message(user["chat_id"], msg)
                await update_task_reminder(t["task_id"], '2day', today_str)

            if delay == 0 and 'deadline' not in t["reminders"]:
                msg = get_random_message("روز تحویل", title=t["title"], date=t["date_fa"], time=t["time"])
                buttons = [
                    [{"text": "تحویل دادم ✅", "callback_data": f"done|{t['task_id']}"}],
                    [{"text": "ندادم ⏰", "callback_data": f"notyet|{t['task_id']}"}]
                ]
                for user in team_members:
                    await send_buttons(user["chat_id"], msg, buttons)
                await update_task_reminder(t["task_id"], 'deadline', today_str)

            if 1 <= delay <= 5 and delay not in t["reminders"].get('delays', []):
                msg = get_random_message("یادآوری تاخیر", title=t["title"], date=t["date_fa"], time=t["time"], delay=delay)
                for user in team_members:
                    await send_message(user["chat_id"], msg)
                await update_task_reminder(t["task_id"], 'delays', delay)

            if delay > 5 and 'alert' not in t["reminders"]:
                msg = get_random_message("هشدار مدیر", title=t["title"], team=t["team"], date=t["date_fa"], delay=delay)
                for admin in admins:
                    await send_message(admin["chat_id"], msg)
                await update_task_reminder(t["task_id"], 'alert', today_str)
        except Exception as e:
            log_error(f"Reminder error for task {t['task_id']}: {e}")
