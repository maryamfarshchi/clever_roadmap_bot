# app/core/logging.py
# -*- coding: utf-8 -*-

import logging
import os

log_dir = 'app/logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(log_dir, 'bot.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_info(msg: str):
    logging.info(msg)

def log_error(msg: str):
    logging.error(msg)
