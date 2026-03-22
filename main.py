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

from app.main import AdilSecmeliApp

if __name__ == "__main__":
    app = AdilSecmeliApp()
    app.mainloop()
