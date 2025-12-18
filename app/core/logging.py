# app/core/logging.py
import logging
from datetime import datetime
import pytz

IRAN_TZ = pytz.timezone("Asia/Tehran")

logging.basicConfig(
    filename='app/logs/bot.log',  # فولدر logs بساز
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_info(msg):
    logging.info(msg)

def log_error(msg):
    logging.error(msg)

# در جاهای کد (مثل sheets.py یا job.py)، print رو با log_error جایگزین کن، مثلاً:
# log_error(f"get_sheet ERROR: {e}")
