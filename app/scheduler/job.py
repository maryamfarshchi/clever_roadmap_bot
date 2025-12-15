# app/scheduler/job.py
# -*- coding: utf-8 -*-

from bot.handler import send_daily_reminders

# اگر weekly هنوز نیاز داری، می‌تونی بعداً send_week رو در handler اضافه کنی
# فعلاً خالی گذاشتم تا ارور نده (main.py هنوز import می‌کنه)

def run_weekly_jobs():
    print("[WEEKLY JOB] No weekly action defined yet (you can add send_week later if needed)")

# اجرای روزانه: هر روز ساعت ۹ صبح، پیام‌های PRE2/DUE/OVR/ESC از شیت Messages با فلگ و دکمه‌ها
def run_daily_jobs():
    print("[DAILY JOB] Starting daily reminders (PRE2, DUE, OVR, ESC) at 9 AM...")
    try:
        send_daily_reminders()
        print("[DAILY JOB] Daily reminders sent successfully")
    except Exception as e:
        print(f"[DAILY JOB ERROR] {str(e)}")
