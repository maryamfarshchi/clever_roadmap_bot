# app/core/sheets.py
# -*- coding: utf-8 -*-

import os
import requests

API = os.getenv("GOOGLE_API_URL", "").rstrip("/")

def get_sheet(sheet):
    try:
        url = f"{API}?sheet={sheet}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "error" in data or "rows" not in data:
            print(f"Sheet Error: {data}")
            return []

        return data["rows"]
    except Exception as e:
        print(f"get_sheet ERROR: {e}")
        return []

def append_row(sheet, row):
    try:
        payload = {"sheet": sheet, "row": row}
        requests.post(f"{API}", json=payload, timeout=10)
    except Exception as e:
        print(f"append_row ERROR: {e}")

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
        requests.post(f"{API}", json=payload, timeout=10)
    except Exception as e:
        print(f"update_cell ERROR: {e}")
