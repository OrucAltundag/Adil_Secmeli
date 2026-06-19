# -*- coding: utf-8 -*-
"""
AHP Agirlik Yonetimi sayfasinin TUM islemlerini headless test eder.
Tkinter withdrawn root + mock app + monkeypatch messagebox/simpledialog.
Her buton/islem icin PASS/FAIL raporu uretir.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import tkinter as tk
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SRC_DB = os.path.join(os.path.dirname(__file__), "..", "data", "adil_secmeli.db")
TMP_DB = os.path.join(tempfile.gettempdir(), "ahp_test_copy.db")
shutil.copy2(SRC_DB, TMP_DB)

from app.ui.tabs import ahp_weight_page as M

# ── messagebox / simpledialog mock ───────────────────────────────────────────
_dialog_log = []


def _mb(kind):
    def f(*a, **k):
        _dialog_log.append((kind, a[:2]))
        return True if kind == "askyesno" else "OK"
    return f


M.messagebox.showinfo = _mb("info")
M.messagebox.showwarning = _mb("warn")
M.messagebox.showerror = _mb("error")
M.messagebox.askyesno = _mb("askyesno")

_ask_answers = {"name": "TestProfil", "default": "Test"}


def _askstring(title, prompt, **k):
    _dialog_log.append(("askstring", (title, prompt)))
    if "ad" in str(prompt).lower():
        return "OtomatikTestProfil"
    if "gerekce" in str(prompt).lower():
        return "test red gerekcesi"
    return k.get("initialvalue") or "TestDeger"


M.simpledialog.askstring = _askstring


class MockDB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)


class MockApp:
    def __init__(self, path):
        self.db = MockDB(path)
        self.db_path = path
        self.app_config = None


# ── Test calistirici ─────────────────────────────────────────────────────────
sonuclar = []


def T(ad, fn):
    _dialog_log.clear()
    try:
        fn()
        son = _dialog_log[-1] if _dialog_log else None
        if son and son[0] == "error":
            sonuclar.append(("FAIL", ad, f"error dialog: {son[1]}"))
        else:
            sonuclar.append(("PASS", ad, son[0] if son else "ok"))
    except Exception as e:
        sonuclar.append(("FAIL", ad, f"{type(e).__name__}: {e}"))
        traceback.print_exc()


def main():
    root = tk.Tk()
    root.withdraw()
    app = MockApp(TMP_DB)
    page = M.AHPWeightPage(root, app=app)  # type: ignore[arg-type]  # tk.Tk runtime icin gecerli parent

    cur = app.db.conn.cursor()

    def aktif_olmayan_id():
        cur.execute(
            "SELECT id FROM ahp_weight_profiles WHERE is_active=0 ORDER BY id LIMIT 1"
        )
        r = cur.fetchone()
        return r[0] if r else None

    def aktif_id():
        cur.execute("SELECT id FROM ahp_weight_profiles WHERE is_active=1 LIMIT 1")
        r = cur.fetchone()
        return r[0] if r else None

    def sec(pid):
        """Treeview'de pid'li profili sec."""
        for item, p in page._profile_rows.items():
            if int(p) == int(pid):
                page.profile_tree.selection_set(item)
                page.profile_tree.focus(item)
                return True
        return False

    # 1) refresh / liste
    T("refresh()", page.refresh)
    cur.execute("SELECT COUNT(*) FROM ahp_weight_profiles")
    print(f"  [bilgi] baslangic profil sayisi: {cur.fetchone()[0]}")

    # 2) Yeni profil olustur (simpledialog -> 'OtomatikTestProfil')
    T("create_default_profile()", page.create_default_profile)

    # 3) Yeni olusan profili sec
    cur.execute(
        "SELECT id FROM ahp_weight_profiles WHERE profile_name='OtomatikTestProfil' "
        "ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    yeni_id = row[0] if row else None
    print(f"  [bilgi] olusan test profil id: {yeni_id}")

    if yeni_id:
        sec(yeni_id)
        T("_on_profile_select()", page._on_profile_select)
        T("validate_selected()", page.validate_selected)
        sec(yeni_id)
        T("submit_selected()", page.submit_selected)
        sec(yeni_id)
        T("approve_selected()", page.approve_selected)
        sec(yeni_id)
        T("activate_selected()", page.activate_selected)
        sec(yeni_id)
        T("rename_selected()", page.rename_selected)
        sec(yeni_id)
        T("clone_selected()", page.clone_selected)
        sec(yeni_id)
        T("_edit_selected_in_tab2()", page._edit_selected_in_tab2)

    # 4) Matris islemleri (Tab2)
    T("calculate_current_matrix()", page.calculate_current_matrix)
    T("apply_pairwise_value()", page.apply_pairwise_value)
    T("_reset_matrix()", page._reset_matrix)
    T("save_matrix_to_selected(False) [Sadece Kaydet]",
      lambda: page.save_matrix_to_selected(False))
    T("save_and_approve_matrix() [Kaydet+Onayla]",
      page.save_and_approve_matrix)

    # 5) _editing_profile() KENAR DURUM: editing id = None ve secim yok
    page._editing_profile_id = None
    page.profile_tree.selection_remove(*page.profile_tree.selection())
    ep = page._editing_profile()
    if ep and int(ep.get("id") or 0) > 0:
        sonuclar.append(("PASS", "_editing_profile() fallback (secim yok)",
                          f"aktif/ilk profile dustu id={ep['id']}"))
    else:
        sonuclar.append(("FAIL", "_editing_profile() fallback (secim yok)",
                          f"gecersiz: {ep}"))

    # 6) _editing_profile() KENAR DURUM: editing id = 0 (eski bug)
    page._editing_profile_id = 0
    ep0 = page._editing_profile()
    if ep0 and int(ep0.get("id") or 0) > 0:
        sonuclar.append(("PASS", "_editing_profile() id=0 bug korumasi",
                          f"gecerli profile dustu id={ep0['id']}"))
    else:
        sonuclar.append(("FAIL", "_editing_profile() id=0 bug korumasi",
                          f"hala gecersiz: {ep0}"))

    # 7) Arsivle + Sil + Reddet(=Sil) — aktif olmayan profil uzerinde
    page._editing_profile_id = None
    pid = aktif_olmayan_id()
    if pid:
        sec(pid)
        T("archive_selected()", page.archive_selected)
    pid = aktif_olmayan_id()
    if pid:
        sec(pid)
        T("delete_selected()", page.delete_selected)
    pid = aktif_olmayan_id()
    if pid:
        sec(pid)
        T("reject_selected() [=Sil]", page.reject_selected)

    # 8) Aktif profili silmeye calis -> engellenmelii
    aid = aktif_id()
    if aid:
        sec(aid)
        _dialog_log.clear()
        try:
            page.delete_selected()
            son = _dialog_log[-1] if _dialog_log else None
            # error/warn beklenir (aktif silinemez)
            if son and son[0] in ("error", "warn"):
                sonuclar.append(("PASS", "Aktif profil silme korumasi",
                                 "engellendi (beklenen)"))
            else:
                # gercekten silindi mi kontrol
                cur.execute("SELECT COUNT(*) FROM ahp_weight_profiles WHERE id=?", (aid,))
                if cur.fetchone()[0] == 1:
                    sonuclar.append(("PASS", "Aktif profil silme korumasi",
                                     "profil duruyor"))
                else:
                    sonuclar.append(("FAIL", "Aktif profil silme korumasi",
                                     "AKTIF PROFIL SILINDI!"))
        except Exception as e:
            sonuclar.append(("FAIL", "Aktif profil silme korumasi", str(e)))

    T("load_impact()", page.load_impact)
    T("final refresh()", page.refresh)

    root.destroy()

    # ── Rapor ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("AHP SAYFASI ISLEM TEST RAPORU")
    print("=" * 64)
    p = sum(1 for s in sonuclar if s[0] == "PASS")
    f = sum(1 for s in sonuclar if s[0] == "FAIL")
    for durum, ad, detay in sonuclar:
        isaret = "OK  " if durum == "PASS" else "FAIL"
        print(f"  [{isaret}] {ad:<48} {detay}")
    print("-" * 64)
    print(f"TOPLAM: {p} PASS, {f} FAIL")
    return 0 if f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
