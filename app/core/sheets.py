# app/core/sheets.py
# -*- coding: utf-8 -*-

import os
import requests

# تمیز کردن URL (حذف / و ? آخر اگر باشه)
API = os.getenv("GOOGLE_API_URL", "").rstrip("/").split('?')[0]

# ----------------------------------------------------
# دریافت داده از یک شیت
# ----------------------------------------------------
def get_sheet(sheet):
    try:
        url = f"{API}?sheet={sheet}"
        print(f"[DEBUG] Fetching sheet: {url}")  # دیباگ برای چک URL
        response = requests.get(url, timeout=10)
        data = response.json()

        if "rows" not in data:
            print("Sheet Error:", data)
            return []

        print(f"[DEBUG] Sheet {sheet} loaded successfully, rows: {len(data['rows'])}")
        return data["rows"]

    except Exception as e:
        print("get_sheet ERROR:", e)
        return []

# ----------------------------------------------------
# اضافه کردن یک ردیف جدید در شیت
# ----------------------------------------------------
def append_row(sheet, row):
    try:
        payload = {"sheet": sheet, "row": row}
        requests.post(API, json=payload, timeout=10)
    except Exception as e:
        print("append_row ERROR:", e)

# ----------------------------------------------------
# آپدیت یک سلول مشخص (rowIndex, colIndex)
# index از 1 شروع می‌شود (مثل گوگل‌شیت)
# ----------------------------------------------------
def update_cell(sheet, row_index, col_index, value):
    try:
        payload = {
            "sheet": sheet,
            "update": {
                "row": row_index,
                "col": col_index,
                "value": value,
            },
        }
        requests.post(API, json=payload, timeout=10)
    except Exception as e:
        print("update_cell ERROR:", e)
