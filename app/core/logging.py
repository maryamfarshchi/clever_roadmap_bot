# app/core/logging.py
import logging
from datetime import datetime
import pytz
import os  # اضافه‌شده

IRAN_TZ = pytz.timezone("Asia/Tehran")

# ساخت فولدر logs اگر وجود نداشت
log_dir = 'app/logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)  # فولدر رو می‌سازه

logging.basicConfig(
    filename=os.path.join(log_dir, 'bot.log'),  # مسیر کامل
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_info(msg):
    logging.info(msg)

def log_error(msg):
    logging.error(msg)
