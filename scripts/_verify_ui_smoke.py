# -*- coding: utf-8 -*-
"""Geçici doğrulama: değişen Tk sayfalarını gerçekten örnekle + render et."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import load_app_config  # noqa: E402

DB = str(ROOT / "data" / "adil_secmeli.db")


class StubApp:
    def __init__(self):
        self.db_path = DB
        self.app_config = load_app_config()
        self.db = None
        self.user_context = None


def run():
    root = tk.Tk()
    root.withdraw()
    app = StubApp()
    results = []

    # 1) DataQualityPage — refactor edilen sorgular + render
    try:
        from app.ui.tabs.data_quality_page import DataQualityPage
        p = DataQualityPage(root, app=app, db_path=DB)
        p._populate_years()
        p._populate_faculties()
        p._generate_report()
        results.append(("DataQualityPage refresh+report", "OK"))
    except Exception as e:
        results.append(("DataQualityPage", f"FAIL: {type(e).__name__}: {e}"))

    # 2) SystemHealthPage — kartlar + renklendirme + yedek butonu var mı
    try:
        from app.ui.tabs.system_health_page import SystemHealthPage
        h = SystemHealthPage(root, app=app)
        assert getattr(h, "_cards", None), "özet kartları yok"
        assert hasattr(h, "_manual_backup"), "yedek handler yok"
        assert hasattr(h, "_colorize_report"), "renklendirme yok"
        # hızlı sağlık çalıştır (senkron yol: doğrudan servis)
        rep = h._health_service().run_quick_health_check()
        h._update_cards(rep)
        from app.health.health_formatter import format_report
        h._set_text(h.txt_report, format_report(rep, developer=False))
        h._colorize_report(h.txt_report)
        results.append((f"SystemHealthPage kart+renk (skor {rep.score:.0f})", "OK"))
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("SystemHealthPage", f"FAIL: {type(e).__name__}: {e}"))

    # 3) TrendVisualizationPage — Veri altına eklenen örnek
    try:
        from app.ui.tabs.trend_visualization_page import TrendVisualizationPage
        t = TrendVisualizationPage(root, app=app)
        t._load_years()
        t._load_faculties()
        results.append(("TrendVisualizationPage init+load", "OK"))
    except Exception as e:
        import traceback; traceback.print_exc()
        results.append(("TrendVisualizationPage", f"FAIL: {type(e).__name__}: {e}"))

    # 4) DataManagementPage — rollback/onay sekmesi
    try:
        from app.ui.tabs.data_management_page import DataManagementPage
        DataManagementPage(root, app=app)
        results.append(("DataManagementPage init", "OK"))
    except Exception as e:
        results.append(("DataManagementPage", f"FAIL: {type(e).__name__}: {e}"))

    root.destroy()
    print("\n=== UI SMOKE SONUÇ ===")
    ok = 0
    for name, status in results:
        print(f"[{'OK ' if status == 'OK' else 'FAIL'}] {name}: {status}")
        ok += status == "OK"
    print(f"\n{ok}/{len(results)} sayfa sorunsuz")
    return ok == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
