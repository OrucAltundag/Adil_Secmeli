# -*- coding: utf-8 -*-
"""AHP Ağırlık Yönetimi Tkinter paneli."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from app.services.ahp_calculation_service import calculate_weights_from_pairwise_matrix
from app.services.ahp_impact_explanation_service import explain_weight_profile
from app.services.ahp_profile_service import (
    activate_profile,
    approve_profile,
    archive_profile,
    clone_profile,
    create_profile,
    get_profile,
    list_ahp_profiles,
    reject_profile,
    submit_for_approval,
    validate_profile,
)
from app.services.criteria_definition_service import list_active_criteria


class AHPWeightPage(ttk.Frame):
    """Karar Merkezi dışında kullanılabilen AHP profil ve ikili karşılaştırma ekranı."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._profile_rows: dict[str, int] = {}
        self._criterion_keys: list[str] = []
        self._build_ui()

    def _conn(self):
        conn = getattr(getattr(self.app, "db", None), "conn", None)
        if conn is None:
            raise RuntimeError("Veritabanı bağlantısı yok.")
        return conn

    def _build_ui(self):
        header = ttk.Frame(self, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(header, text="AHP Ağırlık Yönetimi", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Yenile", command=self.refresh).pack(side=tk.RIGHT)
        ttk.Button(header, text="Yeni Profil", command=self.create_default_profile).pack(side=tk.RIGHT, padx=4)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._build_profiles_tab()
        self._build_wizard_tab()
        self._build_impact_tab()

    def _build_profiles_tab(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Profil Listesi")
        columns = ("name", "scope", "year", "version", "source", "cr", "status", "active")
        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.profile_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
        headings = {
            "name": "Profil",
            "scope": "Kapsam",
            "year": "Yıl",
            "version": "Versiyon",
            "source": "Kaynak",
            "cr": "CR",
            "status": "Durum",
            "active": "Aktif",
        }
        for col, text in headings.items():
            self.profile_tree.heading(col, text=text)
            self.profile_tree.column(col, width=120, anchor=tk.W)
        self.profile_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.profile_tree.yview)
        self.profile_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.profile_tree.bind("<<TreeviewSelect>>", lambda _e: self.load_selected_profile())

        actions = ttk.Frame(frame, padding=(0, 6, 0, 0))
        actions.pack(fill=tk.X)
        for text, command in [
            ("Validate Et", self.validate_selected),
            ("Onaya Gönder", self.submit_selected),
            ("Onayla", self.approve_selected),
            ("Reddet", self.reject_selected),
            ("Aktif Yap", self.activate_selected),
            ("Klonla", self.clone_selected),
            ("Arşivle", self.archive_selected),
        ]:
            ttk.Button(actions, text=text, command=command).pack(side=tk.LEFT, padx=3)

    def _build_wizard_tab(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="İkili Karşılaştırma")
        top = ttk.Frame(frame)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Kriter A").pack(side=tk.LEFT)
        self.cb_left = ttk.Combobox(top, width=18, state="readonly")
        self.cb_left.pack(side=tk.LEFT, padx=4)
        ttk.Label(top, text="Kriter B").pack(side=tk.LEFT)
        self.cb_right = ttk.Combobox(top, width=18, state="readonly")
        self.cb_right.pack(side=tk.LEFT, padx=4)
        ttk.Label(top, text="Önem").pack(side=tk.LEFT)
        self.cb_saaty = ttk.Combobox(
            top,
            width=22,
            state="readonly",
            values=[
                "1 - Eşit önemli",
                "3 - Biraz daha önemli",
                "5 - Güçlü önemli",
                "7 - Çok güçlü önemli",
                "9 - Aşırı önemli",
                "1/3 - Ters biraz önemli",
                "1/5 - Ters güçlü önemli",
                "1/7 - Ters çok güçlü önemli",
                "1/9 - Ters aşırı önemli",
            ],
        )
        self.cb_saaty.set("1 - Eşit önemli")
        self.cb_saaty.pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Matris Değerini Uygula", command=self.apply_pairwise_value).pack(side=tk.LEFT, padx=4)

        ttk.Label(frame, text="Matris JSON").pack(anchor=tk.W, pady=(10, 2))
        self.matrix_text = tk.Text(frame, height=10, wrap=tk.NONE)
        self.matrix_text.pack(fill=tk.BOTH, expand=True)
        bottom = ttk.Frame(frame)
        bottom.pack(fill=tk.X, pady=6)
        ttk.Button(bottom, text="Ağırlıkları Hesapla", command=self.calculate_current_matrix).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Seçili Profile Kaydet", command=self.save_matrix_to_selected).pack(side=tk.LEFT, padx=4)
        self.result_text = tk.Text(frame, height=6, wrap=tk.WORD)
        self.result_text.pack(fill=tk.X)

    def _build_impact_tab(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Etki ve Sensitivity")
        self.impact_text = tk.Text(frame, height=18, wrap=tk.WORD)
        self.impact_text.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="Seçili Profil Etkisini Göster", command=self.load_impact).pack(anchor=tk.E, pady=6)

    def refresh(self):
        try:
            conn = self._conn()
            profiles = list_ahp_profiles(conn)
            criteria = list_active_criteria(conn)
            conn.commit()
            self._criterion_keys = [row["criterion_key"] for row in criteria]
            self.cb_left["values"] = self._criterion_keys
            self.cb_right["values"] = self._criterion_keys
            if self._criterion_keys:
                self.cb_left.set(self._criterion_keys[0])
                self.cb_right.set(self._criterion_keys[min(1, len(self._criterion_keys) - 1)])
            for item in self.profile_tree.get_children():
                self.profile_tree.delete(item)
            self._profile_rows.clear()
            for profile in profiles:
                item = self.profile_tree.insert(
                    "",
                    tk.END,
                    values=(
                        profile.get("profile_name"),
                        self._scope_text(profile),
                        profile.get("year") or "",
                        profile.get("version"),
                        profile.get("source"),
                        "" if profile.get("consistency_ratio") is None else f"{float(profile['consistency_ratio']):.3f}",
                        profile.get("status"),
                        "Evet" if profile.get("is_active") else "Hayır",
                    ),
                )
                self._profile_rows[item] = int(profile["id"])
        except Exception as exc:
            messagebox.showerror("AHP Ağırlık Yönetimi", str(exc))

    def load_selected_profile(self):
        profile = self._selected_profile()
        if not profile:
            return
        self.matrix_text.delete("1.0", tk.END)
        self.matrix_text.insert(tk.END, json.dumps(profile.get("pairwise_matrix") or [], ensure_ascii=False, indent=2))
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, json.dumps(profile.get("weights") or {}, ensure_ascii=False, indent=2))

    def create_default_profile(self):
        try:
            conn = self._conn()
            profile = create_profile(
                conn,
                profile_name="Yeni AHP Profili",
                criteria_keys=self._criterion_keys or None,
                source="manual",
                notes="UI üzerinden oluşturuldu.",
            )
            conn.commit()
            self.refresh()
            messagebox.showinfo("AHP Ağırlık Yönetimi", f"Profil oluşturuldu: #{profile['id']}")
        except Exception as exc:
            messagebox.showerror("AHP Ağırlık Yönetimi", str(exc))

    def apply_pairwise_value(self):
        keys = self._criterion_keys or list(self.cb_left["values"])
        if not keys:
            return
        left = self.cb_left.get()
        right = self.cb_right.get()
        if left == right:
            messagebox.showwarning("AHP", "Aynı kriter için karşılaştırma yapılmaz; diagonal 1 kalır.")
            return
        matrix = self._current_matrix(keys)
        value = self._saaty_value()
        i = keys.index(left)
        j = keys.index(right)
        matrix[i][j] = value
        matrix[j][i] = 1.0 / value
        self.matrix_text.delete("1.0", tk.END)
        self.matrix_text.insert(tk.END, json.dumps(matrix, ensure_ascii=False, indent=2))

    def calculate_current_matrix(self):
        try:
            keys = self._criterion_keys or list(self.cb_left["values"])
            matrix = self._current_matrix(keys)
            result = calculate_weights_from_pairwise_matrix(keys, matrix)
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        except Exception as exc:
            messagebox.showerror("AHP Hesaplama", str(exc))

    def save_matrix_to_selected(self):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", "Önce bir profil seçin.")
            return
        try:
            keys = profile.get("criteria_keys") or self._criterion_keys
            matrix = self._current_matrix(keys)
            from app.services.ahp_profile_service import update_profile

            conn = self._conn()
            update_profile(conn, int(profile["id"]), criteria_keys=keys, pairwise_matrix=matrix)
            conn.commit()
            self.refresh()
            messagebox.showinfo("AHP", "Matris profile kaydedildi ve doğrulandı.")
        except Exception as exc:
            messagebox.showerror("AHP", str(exc))

    def validate_selected(self):
        self._profile_action(lambda conn, pid: validate_profile(conn, pid), "Profil doğrulandı.")

    def submit_selected(self):
        self._profile_action(lambda conn, pid: submit_for_approval(conn, pid), "Profil onaya gönderildi.")

    def approve_selected(self):
        self._profile_action(lambda conn, pid: approve_profile(conn, pid, approved_by="ui"), "Profil onaylandı.")

    def reject_selected(self):
        reason = simpledialog.askstring("AHP Reddet", "Red gerekçesi")
        if not reason:
            return
        self._profile_action(lambda conn, pid: reject_profile(conn, pid, reason, rejected_by="ui"), "Profil reddedildi.")

    def activate_selected(self):
        self._profile_action(lambda conn, pid: activate_profile(conn, pid, actor="ui"), "Profil aktif yapıldı.")

    def clone_selected(self):
        self._profile_action(lambda conn, pid: clone_profile(conn, pid, actor="ui"), "Profil klonlandı.")

    def archive_selected(self):
        self._profile_action(lambda conn, pid: archive_profile(conn, pid, actor="ui"), "Profil arşivlendi.")

    def load_impact(self):
        profile = self._selected_profile()
        if not profile:
            return
        try:
            report = explain_weight_profile(self._conn(), int(profile["id"]))
            self.impact_text.delete("1.0", tk.END)
            self.impact_text.insert(tk.END, report["summary_text"] + "\n\n")
            for row in report["weight_table"]:
                self.impact_text.insert(tk.END, f"- {row['criterion_key']}: %{row['percent']}\n")
        except Exception as exc:
            messagebox.showerror("AHP Etki", str(exc))

    def _profile_action(self, action, message: str):
        profile = self._selected_profile()
        if not profile:
            messagebox.showwarning("AHP", "Önce bir profil seçin.")
            return
        try:
            conn = self._conn()
            action(conn, int(profile["id"]))
            conn.commit()
            self.refresh()
            messagebox.showinfo("AHP", message)
        except Exception as exc:
            messagebox.showerror("AHP", str(exc))

    def _selected_profile(self):
        selected = self.profile_tree.selection()
        if not selected:
            return None
        profile_id = self._profile_rows.get(selected[0])
        return get_profile(self._conn(), int(profile_id)) if profile_id else None

    def _current_matrix(self, keys):
        raw = self.matrix_text.get("1.0", tk.END).strip()
        if raw:
            return json.loads(raw)
        return [[1.0 if i == j else 1.0 for j in range(len(keys))] for i in range(len(keys))]

    def _saaty_value(self) -> float:
        raw = self.cb_saaty.get().split(" - ")[0].strip()
        if "/" in raw:
            left, right = raw.split("/", 1)
            return float(left) / float(right)
        return float(raw)

    def _scope_text(self, profile):
        parts = [str(profile.get("scope_type") or "global")]
        if profile.get("faculty_id"):
            parts.append(f"F:{profile['faculty_id']}")
        if profile.get("department_id"):
            parts.append(f"B:{profile['department_id']}")
        if profile.get("semester"):
            parts.append(str(profile["semester"]))
        return " / ".join(parts)
