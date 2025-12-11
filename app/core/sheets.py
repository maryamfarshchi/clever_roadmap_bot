# app/core/sheets.py
import os
import requests

API = os.getenv("GOOGLE_API_URL", "").rstrip("/")


# -------------------------
#  دریافت داده از یک شیت
# -------------------------
def get_sheet(sheet):
    try:
        url = f"{API}?sheet={sheet}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "rows" not in data:
            print("Sheet Error:", data)
            return []

        return data["rows"]

    except Exception as e:
        print("get_sheet ERROR:", e)
        return []


# -------------------------
#  اضافه کردن یک ردیف
# -------------------------
def append(sheet, row):
    try:
        payload = {"sheet": sheet, "row": row}
        requests.post(API, json=payload, timeout=10)
    except Exception as e:
        print("append ERROR:", e)
