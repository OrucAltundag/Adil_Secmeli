# -*- coding: utf-8 -*-
"""Sistem Sağlığı ve mimari denetim paneli (uygulama sağlık merkezi).

Bu sayfa güncel sağlık raporunu, karşılaştırma için bir önceki sağlık
raporunu ve algoritma kataloğunu sunar. Sağlık kontrolleri ayrı bir iş
parçacığında çalışır; UI donmaz.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.core.config import load_app_config
from app.core.permissions import UserContext
from app.services.service_factory import get_service_factory


def format_report_snapshot(report, *, developer: bool = False) -> str:
    """Karşılaştırma sekmesi için bir önceki sağlık raporunu başlıkla biçimlendirir."""

    from app.health.health_formatter import format_report

    lines = [
        "ÖNCEKİ SAĞLIK KONTROLÜ",
        "=" * 50,
        "Bu sekme, son başarılı kontrolden hemen önceki sağlık raporunu gösterir.",
        "Yeni değerler 'Sağlık Raporu' sekmesinde kalır.",
        "",
        f"Önceki Mod    : {report.mode}",
        f"Önceki Durum  : {report.overall_status}",
        f"Önceki Puan   : {report.score:.0f} / 100",
        f"Önceki Test   : {report.total_checks}",
        f"Önceki Tarih  : {report.generated_at}",
        "",
    ]
    return "\n".join(lines) + format_report(report, developer=developer)


class SystemHealthPage(ttk.Frame):
    def __init__(self, parent, app=None, system_service=None, user_context=None, config=None):
        super().__init__(parent)
        self.app = app
        self.config = config or getattr(app, "app_config", None) or load_app_config()
        self.user_context = (
            user_context
            or getattr(app, "user_context", None)
            or UserContext.demo_admin(self.config)
        )
        self._system_service = system_service
        self._running = False
        self._last_report = None
        self._previous_report = None
        self._result_queue: "queue.Queue" = queue.Queue()
        self._buttons: list[ttk.Button] = []
        self._build_ui()
        # Açılışta hafif (quick) sağlık kontrolü ve eski özet — UI'ı bloklamaz.
        self.after(400, self._initial_load)

    # -- Servisler ---------------------------------------------------------------
    def _factory(self):
        db_path = getattr(self.app, "db_path", None)
        return get_service_factory(db_path=db_path, config=self.config)

    def _service(self):
        if self._system_service is not None:
            return self._system_service
        return self._factory().get_system_service()

    def _health_service(self):
        return self._factory().get_health_service(user_context=self.user_context)

    # -- UI kurulumu -------------------------------------------------------------
    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Sistem Sağlığı", style="Header.TLabel").pack(side=tk.LEFT)

        self.dev_detail = tk.BooleanVar(
            value=bool(self.config.enable_developer_tools or self.config.debug)
        )
        ttk.Checkbutton(
            top, text="Geliştirici Detayı", variable=self.dev_detail,
            command=self._rerender_last,
        ).pack(side=tk.RIGHT, padx=6)

        for text, cmd in (
            ("TXT Dışa Aktar", lambda: self._export("txt")),
            ("JSON Dışa Aktar", lambda: self._export("json")),
            ("Otomatik Düzelt (Güvenli)", self._start_repair),
            ("Denetim (Audit)", lambda: self._start("audit")),
            ("Hızlı Kontrol", lambda: self._start("quick")),
            ("Tam Sağlık Kontrolü", lambda: self._start("full")),
        ):
            btn = ttk.Button(top, text=text, command=cmd)
            btn.pack(side=tk.RIGHT, padx=4)
            self._buttons.append(btn)

        status = ttk.Frame(self, padding=(8, 0))
        status.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="Hazır. 'Tam Sağlık Kontrolü' ile başlayın.")
        ttk.Label(status, textvariable=self.status_var).pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=160)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.txt_report = self._make_text_tab("Sağlık Raporu")
        self.txt_legacy = self._make_text_tab("Özet (Eski)")
        self.txt_algos = self._make_text_tab("Algoritmalar")

        self.txt_report.insert(
            tk.END, "Sağlık raporu için 'Tam Sağlık Kontrolü' düğmesine basın.\n"
        )
        self._populate_algorithms()
        self._render_previous_report()

    def _make_text_tab(self, title: str) -> tk.Text:
        frame = ttk.Frame(self.nb)
        self.nb.add(frame, text=title)
        text = tk.Text(frame, wrap=tk.WORD, height=20)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return text

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.see("1.0")

    # -- Başlangıç / yenileme ----------------------------------------------------
    def _initial_load(self):
        self._render_previous_report()
        self._start("quick")

    def refresh(self):
        """main.py sekme değişiminde çağırır; önceki raporu korur."""
        self._render_previous_report()

    def _render_previous_report(self):
        """Karşılaştırma sekmesini bir önceki başarılı sağlık raporuyla doldurur."""

        if self._previous_report is None:
            if self._last_report is None:
                message = (
                    "Henüz karşılaştırılacak eski sağlık raporu yok.\n\n"
                    "İlk sağlık kontrolü tamamlandığında yeni değerler "
                    "'Sağlık Raporu' sekmesinde görünür. İkinci ve sonraki "
                    "başarılı kontrollerde, bir önceki rapor otomatik olarak "
                    "bu sekmeye taşınır."
                )
            else:
                message = (
                    "Karşılaştırılacak önceki sağlık raporu yok.\n\n"
                    "Bir sağlık kontrolü daha çalıştırıldığında mevcut rapor "
                    "buraya taşınacak, yeni rapor 'Sağlık Raporu' sekmesinde "
                    "kalacaktır."
                )
            self._set_text(self.txt_legacy, message)
            return

        try:
            text = format_report_snapshot(
                self._previous_report, developer=bool(self.dev_detail.get())
            )
            self._set_text(self.txt_legacy, text)
        except Exception as exc:  # noqa: BLE001 - sayfa asla çökmemeli
            self._set_text(
                self.txt_legacy,
                f"Önceki rapor üretilemedi: {type(exc).__name__}: {exc}",
            )

    def _populate_algorithms(self):
        try:
            from app.health.health_formatter import format_algorithm_catalog

            self._set_text(self.txt_algos, format_algorithm_catalog())
        except Exception as exc:  # noqa: BLE001
            self._set_text(
                self.txt_algos,
                f"Algoritma kataloğu yüklenemedi: {type(exc).__name__}: {exc}",
            )

    # -- Sağlık kontrolü (thread) ------------------------------------------------
    def _set_running(self, running: bool):
        self._running = running
        state = tk.DISABLED if running else tk.NORMAL
        for btn in self._buttons:
            try:
                btn.configure(state=state)
            except Exception:
                pass
        if running:
            self.progress.pack(side=tk.RIGHT, padx=8)
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    _MODE_LABELS = {
        "quick": "Hızlı sağlık kontrolü",
        "full": "Tam sağlık kontrolü",
        "audit": "Denetim (audit) taraması",
        "repair": "Güvenli otomatik düzeltme",
    }

    def _start_repair(self):
        if self._running:
            return
        if not messagebox.askyesno(
            "Otomatik Düzeltme",
            "Yalnızca GÜVENLİ düzeltmeler uygulanacak:\n"
            "- Eksik klasörler (logs, reports, backups, exports, health_reports)\n"
            "- Eksik __init__.py\n"
            "- Eksik kozmetik config anahtarı\n\n"
            "Veri/şema/güvenlik ayarı DEĞİŞTİRİLMEZ. Devam edilsin mi?",
        ):
            return
        self._start("repair")

    def _start(self, mode: str):
        if self._running:
            return
        self._set_running(True)
        self.status_var.set(
            f"{self._MODE_LABELS.get(mode, 'Sağlık kontrolü')} çalışıyor…"
        )

        def worker():
            # İş parçacığında YALNIZCA saf Python; Tkinter'a dokunulmaz.
            try:
                svc = self._health_service()
                runner = {
                    "quick": svc.run_quick_health_check,
                    "full": svc.run_full_health_check,
                    "audit": svc.run_audit_health_check,
                    "repair": svc.run_auto_repair,
                }.get(mode, svc.run_full_health_check)
                self._result_queue.put(("ok", runner()))
            except Exception as exc:  # noqa: BLE001
                self._result_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True, name="health-check").start()
        # Sonucu ana iş parçacığında (Tkinter güvenli) periyodik kontrol et.
        self.after(150, self._poll_result)

    def _poll_result(self):
        try:
            kind, payload = self._result_queue.get_nowait()
        except queue.Empty:
            if self._running:
                self.after(150, self._poll_result)
            return
        if kind == "ok":
            self._on_report(payload)
        else:
            self._on_error(payload)

    def _on_error(self, exc: Exception):
        self._set_running(False)
        self.status_var.set("Sağlık kontrolü başarısız.")
        print(f"[SystemHealth] Sağlık kontrolü hatası: {exc}")
        messagebox.showerror("Sistem Sağlığı", "Sağlık kontrolü sırasında hata oluştu. Lütfen daha sonra tekrar deneyin.")

    def _on_report(self, report):
        if self._last_report is not None:
            self._previous_report = self._last_report
        self._last_report = report
        self._set_running(False)
        self.status_var.set(
            f"[{report.mode}] Durum: {report.overall_status}  •  "
            f"Puan: {report.score:.0f}/100  •  Test: {report.total_checks}  •  "
            f"Uyarı: {report.warning_count}  •  Kritik: {report.critical_count}  •  "
            f"Düzeltildi: {report.fixed_count}  •  "
            f"Süre: {report.duration_ms:.0f} ms"
        )
        self._rerender_last()
        self.nb.select(0)

    def _rerender_last(self):
        if self._last_report is None:
            self._render_previous_report()
            return
        try:
            from app.health.health_formatter import format_report

            text = format_report(
                self._last_report, developer=bool(self.dev_detail.get())
            )
            self._set_text(self.txt_report, text)
        except Exception as exc:  # noqa: BLE001
            self._set_text(
                self.txt_report,
                f"Rapor biçimlendirilemedi: {type(exc).__name__}: {exc}",
            )
        self._render_previous_report()

    # -- Dışa aktarma ------------------------------------------------------------
    def _export(self, fmt: str):
        if self._last_report is None:
            messagebox.showinfo(
                "Sistem Sağlığı",
                "Önce bir sağlık kontrolü çalıştırın.",
            )
            return
        ext = ".json" if fmt == "json" else ".txt"
        path = filedialog.asksaveasfilename(
            title="Sağlık Raporunu Kaydet",
            defaultextension=ext,
            initialfile=f"saglik_raporu{ext}",
            filetypes=[("JSON", "*.json")] if fmt == "json" else [("Metin", "*.txt")],
        )
        if not path:
            return
        try:
            svc = self._health_service()
            if fmt == "json":
                result = svc.export_health_report_json(path, self._last_report)
            else:
                result = svc.export_health_report_txt(path, self._last_report)
        except Exception as exc:  # noqa: BLE001
            print(f"[SystemHealth] Rapor dışa aktarma hatası: {exc}")
            messagebox.showerror("Sistem Sağlığı", "Rapor dışa aktarımı başarısız oldu. Lütfen daha sonra tekrar deneyin.")
            return
        if getattr(result, "success", False):
            messagebox.showinfo("Sistem Sağlığı", result.message or "Rapor kaydedildi.")
        else:
            messagebox.showerror(
                "Sistem Sağlığı",
                (result.message if result else "Rapor kaydedilemedi."),
            )
