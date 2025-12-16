# app/scheduler/job.py
# -*- coding: utf-8 -*-

from core.members import get_members_by_team
from bot.handler import send_week, send_pending

TEAMS = ["production", "ai production", "digital"]

def run_weekly_jobs():
    for team in TEAMS:
        members = get_members_by_team(team)
        print(f"[WEEKLY] team={team} members={len(members)}")
        for user in members:
            try:
                send_week(user["chat_id"], user)
            except Exception as e:
                print("[WEEKLY ERROR]", team, user.get("chat_id"), str(e))

def run_daily_jobs():
    for team in TEAMS:
        members = get_members_by_team(team)
        print(f"[DAILY] team={team} members={len(members)}")
        for user in members:
            try:
                send_pending(user["chat_id"], user)
            except Exception as e:
                print("[DAILY ERROR]", team, user.get("chat_id"), str(e))
