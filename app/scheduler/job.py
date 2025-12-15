# app/scheduler/job.py
# -*- coding: utf-8 -*-

from bot.handler import send_daily_reminders, send_week, send_pending

TEAMS = ["production", "ai production", "digital"]

def run_weekly_jobs():
    # اگر weekly خواستی، بعداً اضافه کن
    print("[WEEKLY JOB] Weekly job not fully implemented yet")

def run_daily_jobs():
    print("[DAILY JOB] Starting daily reminders...")
    send_daily_reminders()  # تریگر اصلی روزانه
    print("[DAILY JOB] Finished")
