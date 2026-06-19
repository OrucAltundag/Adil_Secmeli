"""Trend Görselleştirme & Kontrol sayfası.

Kullanıcının bir dersin ağırlıklı trend skorunun NASIL hesaplandığını adım adım
ve görsel olarak izleyebilmesi için tasarlanmıştır. Hangi yıl verilerinin mevcut
olduğunu gösterir ve son 1 / 2 / 3 yıl senaryolarına göre FARKLI görselleştirme
üretir (docx'teki istek). Müfredat üretip yeni yıllar oluşturulduktan sonra
trendin kontrolünü sağlamak için bir gözlem aracıdır.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.services.lr_trend_prediction_service import (
    DEFAULT_MISSING_SCORE,
    predict_next_year_trend,
)
from app.services.trend_analysis_service import (
    TREND_DEFAULT_WEIGHTS,
    course_trend_breakdown,
)

# Trend etiketlerinin kullanıcıya dönük Türkçe karşılıkları ve renkleri.
_LABEL_TR = {
    "rising": ("Yükselişte", "#16a34a"),
    "falling": ("Düşüşte", "#dc2626"),
    "stable": ("Dengeli", "#2563eb"),
    "volatile": ("Dalgalı", "#d97706"),
    "new_course": ("Yeni Ders", "#7c3aed"),
    "insufficient_data": ("Yetersiz Veri", "#6b7280"),
}


class TrendVisualizationPage(ttk.Frame):
    """Ders bazlı ağırlıklı trend hesabını görselleştiren sekme."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = getattr(app, "db", None)
        self._fakulte_map: dict[str, int] = {}
        self._ders_map: dict[str, int] = {}
        self._build_ui()
        self.after(300, self._load_initial)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        top = tk.Frame(self, bg="#0f172a")
        top.pack(fill=tk.X)
        tk.Label(
            top, text="Trend Görselleştirme & Kontrol",
            bg="#0f172a", fg="white", font=("Segoe UI", 12, "bold"), padx=10, pady=8,
        ).pack(side=tk.LEFT)
        tk.Button(
            top, text="Yenile", command=self.refresh,
            bg="#334155", fg="white", relief="flat", cursor="hand2", padx=10,
        ).pack(side=tk.RIGHT, padx=8, pady=6)

        bar = tk.Frame(self, bg="#e2e8f0")
        bar.pack(fill=tk.X)
        tk.Label(bar, text="Yıl:", bg="#e2e8f0").pack(side=tk.LEFT, padx=(10, 2), pady=6)
        self.cb_yil = ttk.Combobox(bar, width=8, state="readonly")
        self.cb_yil.pack(side=tk.LEFT, padx=2)
        self.cb_yil.bind("<<ComboboxSelected>>", self._on_scope_change)
        tk.Label(bar, text="Fakülte:", bg="#e2e8f0").pack(side=tk.LEFT, padx=(10, 2))
        self.cb_fakulte = ttk.Combobox(bar, width=32, state="readonly")
        self.cb_fakulte.pack(side=tk.LEFT, padx=2)
        self.cb_fakulte.bind("<<ComboboxSelected>>", self._on_scope_change)
        tk.Label(bar, text="Ders:", bg="#e2e8f0").pack(side=tk.LEFT, padx=(10, 2))
        self.cb_ders = ttk.Combobox(bar, width=40, state="readonly")
        self.cb_ders.pack(side=tk.LEFT, padx=2)
        tk.Button(
            bar, text="Trendi Göster", command=self._show_trend,
            bg="#2563eb", fg="white", relief="flat", cursor="hand2", padx=12,
        ).pack(side=tk.LEFT, padx=10, pady=6)

        body = tk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)

        # Sol: görsel (Canvas)
        left = tk.Frame(body, bg="white")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(
            left, text="Görselleştirme (yıl bazlı başarı + ağırlıklı katkı)",
            bg="#dbeafe", font=("Segoe UI", 9, "bold"), anchor="w", padx=6,
        ).pack(fill=tk.X)
        self.canvas = tk.Canvas(left, bg="white", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", lambda e: self._redraw())

        # Sağ: adım adım hesap
        right = tk.Frame(body, width=420)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        tk.Label(
            right, text="Nasıl Hesaplandı? (adım adım)",
            bg="#dcfce7", font=("Segoe UI", 9, "bold"), anchor="w", padx=6,
        ).pack(fill=tk.X)
        self.txt = tk.Text(
            right, font=("Consolas", 9), bg="#f8fafc", fg="#1e293b",
            relief="flat", wrap="word", state="disabled",
        )
        self.txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._last_breakdown = None

    # -------------------------------------------------------------- veri yükleme
    def refresh(self):
        self.db = getattr(self.app, "db", None)
        prev_fak = self.cb_fakulte.get()
        prev_ders = self.cb_ders.get()
        self._load_years()
        self._load_faculties()
        if prev_fak and prev_fak in self._fakulte_map:
            self.cb_fakulte.set(prev_fak)
            self._load_curriculum_courses()
            if prev_ders and prev_ders in self._ders_map:
                self.cb_ders.set(prev_ders)

    def _load_initial(self):
        self.db = getattr(self.app, "db", None)
        self._load_years()
        self._load_faculties()

    def _conn_ready(self) -> bool:
        return bool(self.db and getattr(self.db, "conn", None))

    def _load_years(self):
        if not self._conn_ready() or self.db is None:
            return
        try:
            _, rows = self.db.run_sql(
                """
                SELECT DISTINCT yil FROM (
                    SELECT akademik_yil AS yil FROM performans WHERE akademik_yil IS NOT NULL
                    UNION SELECT yil FROM ders_kriterleri WHERE yil IS NOT NULL
                    UNION SELECT akademik_yil FROM mufredat WHERE akademik_yil IS NOT NULL
                ) ORDER BY yil DESC
                """
            )
            vals = [str(int(r[0])) for r in (rows or []) if r and r[0] is not None]
            self.cb_yil["values"] = tuple(vals)
            if vals and not self.cb_yil.get():
                self.cb_yil.set(vals[0])
        except Exception as exc:  # noqa: BLE001
            print(f"[TrendVis] _load_years hata: {exc}")

    def _load_faculties(self):
        if not self._conn_ready() or self.db is None:
            return
        try:
            _, rows = self.db.run_sql("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
            self._fakulte_map = {str(r[1]): int(r[0]) for r in (rows or [])}
            self.cb_fakulte["values"] = tuple(self._fakulte_map.keys())
            if self._fakulte_map and not self.cb_fakulte.get():
                first = next(iter(self._fakulte_map))
                self.cb_fakulte.set(first)
                self._load_curriculum_courses()
        except Exception as exc:  # noqa: BLE001
            print(f"[TrendVis] _load_faculties hata: {exc}")

    def _on_scope_change(self, _event=None):
        self._load_curriculum_courses()

    def _load_curriculum_courses(self):
        if not self._conn_ready() or self.db is None:
            return
        fak = self.cb_fakulte.get()
        fid = self._fakulte_map.get(fak)
        try:
            year = int(self.cb_yil.get())
        except (TypeError, ValueError):
            year = None
        if fid is None or year is None:
            self._ders_map = {}
            self.cb_ders["values"] = ()
            self.cb_ders.set("")
            return
        try:
            _, rows = self.db.run_sql(
                """
                SELECT DISTINCT d.ders_id, d.ad
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                JOIN ders d ON d.ders_id = md.ders_id
                LEFT JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE m.akademik_yil = ?
                  AND (b.fakulte_id = ? OR m.fakulte_id = ?)
                ORDER BY d.ad, d.ders_id
                """,
                (int(year), int(fid), int(fid)),
            )
        except Exception as exc:
            print(f"[TrendVis] mufredat dersleri yuklenemedi: {exc}")
            rows = []
        self._ders_map = {str(r[1]): int(r[0]) for r in (rows or []) if r and r[1]}
        self.cb_ders["values"] = tuple(self._ders_map.keys())
        self.cb_ders.set("")

    # ------------------------------------------------------------------- göster
    def _show_trend(self):
        if not self._conn_ready() or self.db is None:
            self._set_text("Veritabanı bağlantısı yok.")
            return
        ders_ad = self.cb_ders.get()
        ders_id = self._ders_map.get(ders_ad)
        if ders_id is None:
            self._set_text("Lütfen bir ders seçin.")
            return
        try:
            year = int(self.cb_yil.get())
        except (TypeError, ValueError):
            self._set_text("Lütfen geçerli bir yıl seçin.")
            return
        try:
            cur = self.db.conn.cursor()
            breakdown = course_trend_breakdown(cur, int(ders_id), int(year))
            # LR ile bir sonraki yıl tahmini (seçili yıl referans → tahmin yılı = yıl+1)
            lr = predict_next_year_trend(cur, int(ders_id), int(year) + 1)
        except Exception as exc:  # noqa: BLE001
            self._set_text(f"Trend hesaplanamadı: {exc}")
            return
        breakdown["_ders_ad"] = ders_ad
        breakdown["_year"] = year
        breakdown["_lr"] = lr  # grafiğe + metne taşı
        self._last_breakdown = breakdown
        self._redraw()
        self._render_text(breakdown)

    # ------------------------------------------------------------------- çizim
    def _redraw(self):
        b = self._last_breakdown
        c = self.canvas
        c.delete("all")
        if not b:
            return
        w = max(c.winfo_width(), 200)
        h = max(c.winfo_height(), 200)

        values = b.get("values_by_year", {}) or {}
        scenario = b.get("scenario", "none")
        label = b.get("trend_label", "insufficient_data")
        label_tr, label_color = _LABEL_TR.get(label, (label, "#334155"))
        score100 = b.get("trend_score_100", 0.0)

        # Başlık
        c.create_text(
            w / 2, 18,
            text=f"{b.get('_ders_ad', '')}  —  {b.get('_year', '')} referans",
            font=("Segoe UI", 11, "bold"), fill="#0f172a",
        )
        c.create_text(
            w / 2, 38,
            text=f"Trend Skoru: {score100:.1f} / 100   •   Etiket: {label_tr}   •   Veri: {b.get('year_count', 0)} yıl",
            font=("Segoe UI", 10, "bold"), fill=label_color,
        )

        if scenario == "none":
            c.create_text(
                w / 2, h / 2,
                text="Bu ders için geçmiş yıl verisi yok.\nMüfredat üretip yeni yıllar oluşturulduktan sonra burada gözlemlenebilir.",
                font=("Segoe UI", 11), fill="#6b7280", justify="center",
            )
            return

        # Çubuk grafiği alanı
        margin_l, margin_r = 70, 30
        top_y, bottom_y = 70, h - 70
        plot_w = w - margin_l - margin_r
        plot_h = max(bottom_y - top_y, 60)

        # Y ekseni (0..1 başarı oranı) — yatay ızgara
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = bottom_y - frac * plot_h
            c.create_line(margin_l, y, w - margin_r, y, fill="#e5e7eb")
            c.create_text(margin_l - 10, y, text=f"{frac:.2f}", anchor="e", font=("Segoe UI", 8), fill="#94a3b8")

        ordered = sorted(values.items(), key=lambda x: x[0])  # eski -> yeni
        n = len(ordered)
        # En güncel 3 yıl ağırlıklı; step katkılarını yıl->katkı eşle
        steps = {int(s["year"]): s for s in b.get("steps", [])}

        slot = plot_w / max(n, 1)
        bar_w = min(slot * 0.5, 90)

        for i, (yr, val) in enumerate(ordered):
            cx = margin_l + slot * (i + 0.5)
            bar_h = max(2, val * plot_h)
            x0, x1 = cx - bar_w / 2, cx + bar_w / 2
            y0 = bottom_y - bar_h
            step = steps.get(int(yr))
            # Ağırlıklı (son 3) yıllar mavi, hesaba girmeyen eski yıllar gri.
            fill = "#3b82f6" if step else "#cbd5e1"
            c.create_rectangle(x0, y0, x1, bottom_y, fill=fill, outline="")
            # Değer etiketi
            c.create_text(cx, y0 - 10, text=f"{val:.2f}", font=("Segoe UI", 9, "bold"), fill="#1e293b")
            # Yıl etiketi
            c.create_text(cx, bottom_y + 14, text=str(yr), font=("Segoe UI", 9, "bold"), fill="#334155")
            # Ağırlık + katkı etiketi (hesaba giren yıllar)
            if step:
                c.create_text(
                    cx, bottom_y + 30,
                    text=f"ağırlık %{step['norm_weight'] * 100:.0f}",
                    font=("Segoe UI", 8), fill="#2563eb",
                )
                c.create_text(
                    cx, bottom_y + 44,
                    text=f"katkı {step['contribution']:.3f}",
                    font=("Segoe UI", 8), fill="#16a34a",
                )

        # Trend skoru çizgisi (0..1)
        score01 = score100 / 100.0
        ys = bottom_y - score01 * plot_h
        c.create_line(margin_l, ys, w - margin_r, ys, fill=label_color, dash=(5, 3), width=2)
        c.create_text(
            w - margin_r, ys - 9, anchor="e",
            text=f"Ağırlıklı Trend = {score01:.3f}", font=("Segoe UI", 9, "bold"), fill=label_color,
        )

        # LR ile bir sonraki yıl tahmini (mor "Tahmin" çubuğu, kesik kenarlı).
        # Geçmiş gerçek değerlerden ayırt edilebilir biçimde gösterilir.
        lr = b.get("_lr")
        if lr:
            pred100 = float(lr.get("predicted_score_100") or 0.0)
            pred_year = int(lr.get("target_year") or 0)
            pred01 = max(0.0, min(1.0, pred100 / 100.0))
            # Tahmin çubuğunu mevcut son sütunun sağına ekle.
            cx = margin_l + slot * (n + 0.5)
            if cx + bar_w / 2 > w - margin_r:
                cx = w - margin_r - bar_w / 2
            bar_h = max(2, pred01 * plot_h)
            x0, x1 = cx - bar_w / 2, cx + bar_w / 2
            y0 = bottom_y - bar_h
            # LR tahmini: mor doluluk + kesik çerçeve (gerçek değerden ayırt edilsin).
            c.create_rectangle(x0, y0, x1, bottom_y, fill="#a78bfa", outline="#5b21b6", width=2, dash=(4, 2))
            c.create_text(cx, y0 - 10, text=f"{pred01:.2f}", font=("Segoe UI", 9, "bold"), fill="#5b21b6")
            c.create_text(cx, bottom_y + 14, text=f"{pred_year}", font=("Segoe UI", 9, "bold"), fill="#5b21b6")
            c.create_text(
                cx, bottom_y + 30,
                text=f"LR tahmin", font=("Segoe UI", 8, "italic"), fill="#5b21b6",
            )
            c.create_text(
                cx, bottom_y + 44,
                text=f"{pred100:.1f}/100  ({lr.get('direction_label_tr', '')})",
                font=("Segoe UI", 8), fill="#5b21b6",
            )

        # Senaryoya özgü not
        notes = {
            "single": "Tek yıl verisi: ağırlıklandırma yapılamaz, skor = mevcut yıl değeri. Karar temkinli yorumlanmalı.",
            "double": "İki yıl verisi: ağırlıklar (0.50 / 0.30) kullanılabilir yıllara göre yeniden normalize edilir.",
            "triple": "Üç yıl verisi: en güncel yıl %50, önceki %30, en eski %20 ağırlıkla hesaba girer.",
        }
        if scenario in notes:
            c.create_text(
                w / 2, h - 14, text=notes[scenario],
                font=("Segoe UI", 8, "italic"), fill="#64748b",
            )

    # ------------------------------------------------------------------- metin
    def _render_text(self, b: dict):
        lines = []
        lines.append("AĞIRLIKLI TREND HESABI")
        lines.append("=" * 34)
        lines.append(f"Ders        : {b.get('_ders_ad', '')}")
        lines.append(f"Referans yıl: {b.get('_year', '')}")
        lines.append(f"Veri kaynağı: {b.get('data_source', 'yok')}")
        lines.append(f"İlk görülme : {b.get('first_seen_year', '-')}")
        lines.append("")
        values = b.get("values_by_year", {}) or {}
        if values:
            lines.append("Yıl bazlı başarı oranları:")
            for yr, val in sorted(values.items()):
                lines.append(f"   {yr}: {float(val):.3f}")
            lines.append("")

        w1, w2, w3 = TREND_DEFAULT_WEIGHTS
        lines.append(f"Varsayılan ağırlıklar (yeni→eski): {w1}, {w2}, {w3}")
        lines.append("")

        steps = b.get("steps", [])
        if not steps:
            lines.append("Hesaba giren yıl yok (yetersiz/sıfır veri).")
        else:
            lines.append("Formül: Trend = Σ (değer × normalize_ağırlık)")
            wsum = b.get("weight_sum_used", 1.0)
            if abs(wsum - 1.0) > 1e-9:
                lines.append(f"(Kullanılabilir ağırlık toplamı {wsum:.2f} olduğundan yeniden normalize edildi.)")
            lines.append("")
            total = 0.0
            for s in steps:
                total += s["contribution"]
                lines.append(
                    f"   {s['year']}: {s['value']:.3f} × {s['norm_weight']:.3f}"
                    f" = {s['contribution']:.4f}"
                )
            lines.append("   " + "-" * 28)
            lines.append(f"   Toplam (0-1) : {total:.4f}")
            lines.append(f"   100'lük skor : {b.get('trend_score_100', 0.0):.2f}")
        lines.append("")

        label = b.get("trend_label", "insufficient_data")
        label_tr, _ = _LABEL_TR.get(label, (label, "#334155"))
        lines.append(f"Etiket   : {label_tr} ({label})")
        vol = b.get("volatility_score")
        if vol is not None:
            lines.append(f"Dalgalanma (std): {float(vol):.4f}")
        lines.append("")
        lines.append("Açıklama:")
        lines.append(str(b.get("explanation", "")))

        # LR ile bir sonraki yıl tahmini (LR_Trend_Skor_Tahmini_Raporu.docx)
        lr = b.get("_lr") or {}
        if lr:
            lines.append("")
            lines.append("LR İLE SONRAKİ YIL TAHMİNİ")
            lines.append("=" * 34)
            lines.append(f"Tahmin yılı : {lr.get('target_year')}")
            hist_disp = []
            for y in lr.get("history", []):
                mark = "*" if y.get("is_default") else " "
                hist_disp.append(f"{y['year']}={float(y['score']):.1f}{mark}")
            lines.append(f"Geçmiş (3 yıl): {'  '.join(hist_disp)}   (* = varsayılan 50)")
            lines.append(
                f"Model       : y = β0 + β1·x   →   β0 = {lr.get('intercept'):.2f}, "
                f"β1 = {lr.get('slope'):+.3f} puan/yıl"
            )
            pred = float(lr.get('predicted_score_100') or 0.0)
            raw = float(lr.get('raw_prediction') or 0.0)
            line_pred = f"Tahmin      : {pred:.2f} / 100  ({float(lr.get('trend_score_normalized') or 0):.3f} normalize)"
            if lr.get("model_clamped"):
                line_pred += f"   (ham: {raw:.2f} → 0..100'e kırpıldı)"
            lines.append(line_pred)
            lines.append(
                f"Yön / Güven : {lr.get('direction_label_tr')}  |  "
                f"güven={lr.get('confidence')}  |  varsayılana düşen yıl={lr.get('missing_year_count')}"
            )
            lines.append("")
            lines.append("Not:")
            lines.append(str(lr.get("explanation", "")))

        self._set_text("\n".join(lines))

    def _set_text(self, text: str):
        self.txt.config(state="normal")
        self.txt.delete("1.0", tk.END)
        self.txt.insert(tk.END, text)
        self.txt.config(state="disabled")
