# -*- coding: utf-8 -*-
# =============================================================================
# main.py — Proje Giris Noktasi
# =============================================================================
# Proje kokunden "python main.py" ile baslatma kisayolu.
# sys.path ayarini yapip app.main.AdilSecmeliApp sinifini olusturur ve calistirir.
# =============================================================================
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import main as run_main

if __name__ == "__main__":
    raise SystemExit(run_main())
