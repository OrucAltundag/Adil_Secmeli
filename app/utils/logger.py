# -*- coding: utf-8 -*-
# =============================================================================
# app/utils/logger.py — Merkezi Loglama Altyapisi
# =============================================================================
# Dosya (logs/app.log) ve konsola (stdout) cift kanalli loglama.
# log_operation() ile islem bazli yapisal log kaydi olusturulur.
# =============================================================================
import logging
import os
import sys

# Log dizini
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)

logger = logging.getLogger("AdilSecmeli")


def log_operation(operation: str, detail: str = "", success: bool = True):
    """İşlem loglaması - dosya ve konsola yazar."""
    status = "OK" if success else "HATA"
    msg = f"[{status}] {operation}"
    if detail:
        msg += f" | {detail}"
    logger.info(msg)