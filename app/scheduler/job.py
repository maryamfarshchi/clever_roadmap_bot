# app/scheduler/job.py
# -*- coding: utf-8 -*-

from datetime import datetime
import pytz
import asyncio
import os

from core.members import get_members_by_team
from core.tasks import (
    load_tasks,
    update_task_reminder,
    get_tasks_today,
    get_tasks_next_7_days,   # <-- جدید
    group_tasks_by_date,
    format_task_block,
    parse_time_hhmm,
)
from core.messages import get_random_message
from bot.helpers import send_message, send_buttons
from core.logging import log_error, log_info

IRAN_TZ = pytz.timezone("Asia/Tehran")
TEAM_NAMES = ["Production", "AI Production", "Digital"]

reminder_lock = asyncio.Lock()

# ---- تنظیمات ارسال رندوم‌ها ساعت 9 ----
MORNING_HOUR = int(os.getenv("MORNING_HOUR", "9"))
MORNING_WINDOW_MIN = int(os.getenv("MORNING_WINDOW_MIN", "10"))  # مثلا 10 دقیقه اول ساعت 9

def in_morning_window(now: datetime) -> bool:
    return (now.hour == MORNING_HOUR) and (0 <= now.minute < MORNING_WINDOW_MIN)

def task_action_buttons(task_id: str):
    return [
        [{"text": "تحویل دادم ✅", "callback_data": f"done|{task_id}"}],
        [{"text": "تحویل ندادم ⏰", "callback_data": f"notyet|{task_id}"}],
    ]

async def run_daily_jobs():
    """
    هر روز 08:30: لیست امروز (بدون دکمه یا می‌تونی با دکمه هم کنی)
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
                    blocks.append("")
                await send_message(u["chat_id"], "\n".join(blocks).strip())
            except Exception as e:
                log_error(f"Daily job error {u.get('chat_id')}: {e}")

async def run_weekly_jobs():
    """
    هر شنبه ساعت دلخواه: برنامه ۷ روز آینده از همان روز
    """
    for team in TEAM_NAMES:
        members = await get_members_by_team(team)
        for u in members:
            try:
                tasks = await get_tasks_next_7_days(team)  # از امروز تا ۷ روز آینده
                name = u.get("customname") or u.get("name") or "رفیق"

                if not tasks:
                    await send_message(u["chat_id"], f"📅 <b>{name}</b>\nبرای ۷ روز آینده تسکی نداری 👌")
                    continue

                lines = [f"📅 <b>{name}</b>\n🗂️ برنامه ۷ روز آینده ({len(tasks)} تسک):\n"]
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
    - رندوم‌ها (۲ روز قبل، ددلاین بدون ساعت، over_1..over_5) فقط ساعت 9 (پنجره 9:00 تا 9:09)
    - ددلاین با ساعت: هر وقت از زمانش رد شد (با اجرای دوره‌ای reminders)
    - overها هم دکمه دارند
    """
    async with reminder_lock:
        tasks = await load_tasks()

        now = datetime.now(IRAN_TZ)
        today_str = now.strftime("%Y-%m-%d")
        current_hm = (now.hour, now.minute)

        admins = await get_members_by_team("ALL")
        morning_ok = in_morning_window(now)

        for t in tasks:
            if t.get("done"):
                continue

            try:
                delay = int(t.get("delay_days", 0))
                reminders = t.get("reminders") or {}

                reminder_type = None
                reminder_key = None

                # --- 2 روز قبل (رندوم) فقط ساعت 9 ---
                if delay == -2:
                    if not morning_ok:
                        continue
                    reminder_type = "2day"
                    if reminder_type in reminders:
                        continue

                # --- روز ددلاین ---
                elif delay == 0:
                    task_time = t.get("time") or ""
                    parsed = parse_time_hhmm(task_time) if task_time else None

                    if parsed:
                        # ددلاین با ساعت: هر وقت از زمانش گذشت
                        reminder_key = "deadline_time"
                        if str(reminders.get(reminder_key, "")).startswith(today_str):
                            continue
                        if current_hm < parsed:
                            continue
                        reminder_type = "deadline"
                    else:
                        # ددلاین بدون ساعت: فقط ساعت 9
                        reminder_key = "deadline_morning"
                        if reminder_key in reminders:
                            continue
                        if not morning_ok:
                            continue
                        reminder_type = "deadline"

                # --- تاخیر 1 تا 5 (رندوم) فقط ساعت 9 ---
                elif 1 <= delay <= 5:
                    if not morning_ok:
                        continue
                    reminder_type = f"over_{delay}"
                    if reminder_type in reminders:
                        continue

                # --- بیشتر از 5: escalated (فقط مدیرها) ساعت 9 ---
                elif delay > 5:
                    if not morning_ok:
                        continue
                    reminder_type = "escalated"
                    if reminder_type in reminders:
                        continue

                else:
                    continue

                # --- escalated فقط مدیرها ---
                if reminder_type == "escalated":
                    if not admins:
                        continue

                    msg = await get_random_message("escalated", **{
                        "title": t.get("title", ""),
                        "date_fa": t.get("date_fa", ""),
                        "days": delay,
                        "time": t.get("time", ""),
                        "team": t.get("team", ""),
                    })

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
                    log_error(f"No members found for team={t.get('team')} task={t.get('task_id')}")
                    continue

                sent = False
                for u in team_members:
                    name = u.get("customname") or u.get("name") or "رفیق"

                    msg = await get_random_message(reminder_type, **{
                        "name": name,
                        "title": t.get("title", ""),
                        "date_fa": t.get("date_fa", ""),
                        "days": abs(delay) if delay < 0 else delay,
                        "time": t.get("time", ""),
                    })

                    if t.get("type"):
                        msg += f"\n🧩 <b>سبک محتوا:</b> {t['type']}"
                    if t.get("comment"):
                        msg += f"\n💬 <b>توضیحات بیشتر:</b> {t['comment']}"

                    # ✅ همه‌ی ریمایندرها (deadline + 2day + overها) دکمه دارند
                    await send_buttons(u["chat_id"], msg, task_action_buttons(t["task_id"]))
                    sent = True

                # ثبت جلوگیری از تکرار
                if sent:
                    if delay == 0 and (t.get("time") or ""):
                        ok = await update_task_reminder(t["task_id"], "deadline_time", f"{today_str} {t.get('time','')}")
                        log_info(f"Sent deadline_time for {t['task_id']} ok={ok}")
                    elif delay == 0:
                        ok = await update_task_reminder(t["task_id"], "deadline_morning", today_str)
                        log_info(f"Sent deadline_morning for {t['task_id']} ok={ok}")
                    else:
                        ok = await update_task_reminder(t["task_id"], reminder_type, today_str)
                        log_info(f"Sent {reminder_type} for {t['task_id']} ok={ok}")

            except Exception as e:
                log_error(f"Reminder error task={t.get('task_id')}: {e}")
