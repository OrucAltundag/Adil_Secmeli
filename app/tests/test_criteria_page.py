import sqlite3

from app.ui.tabs.criteria_page import CriteriaPage


class _DummyDB:
    def __init__(self, conn):
        self.conn = conn

    def run_sql(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur, cur.fetchall()


class _DummyEntry:
    def __init__(self, value="0", state="normal"):
        self.value = str(value)
        self.state = state

    def delete(self, _start, _end=None):
        self.value = ""

    def insert(self, _index, value):
        self.value = str(value)

    def get(self):
        return self.value

    def config(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs["state"]

    def cget(self, key):
        if key == "state":
            return self.state
        raise KeyError(key)


class _DummyLabel:
    def __init__(self):
        self.options = {}

    def config(self, **kwargs):
        self.options.update(kwargs)

    def cget(self, key):
        return self.options.get(key)


def test_fetch_saved_criteria_uses_named_columns_with_aktif_mi_present():
    conn = sqlite3.connect(":memory:")
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE ders_kriterleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ders_id INTEGER,
                yil INTEGER,
                donem TEXT,
                toplam_ogrenci INTEGER,
                gecen_ogrenci INTEGER,
                basari_ortalamasi REAL,
                kontenjan INTEGER,
                kayitli_ogrenci INTEGER,
                aktif_mi INTEGER DEFAULT 1,
                anket_katilimci INTEGER,
                anket_dersi_secen INTEGER
            );
            INSERT INTO ders_kriterleri
                (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                 kontenjan, kayitli_ogrenci, aktif_mi, anket_katilimci, anket_dersi_secen)
            VALUES
                (557, 2022, 'Güz', 100, 70, 56.0, 120, 100, 1, 100, 20);
            """
        )
        page = CriteriaPage.__new__(CriteriaPage)
        page.db = _DummyDB(conn)

        row = page._fetch_saved_criteria(557, 2022, "Güz")

        assert row == ("Güz", 100, 70, 56.0, 120, 100, 100, 20)
    finally:
        conn.close()


def test_manual_fields_locked_after_import():
    page = CriteriaPage.__new__(CriteriaPage)
    page.ent_anket_dersi_secen = _DummyEntry("20", state="normal")
    page.lbl_anket_kaynak_info = _DummyLabel()

    page._apply_survey_lock_state(True, "Bu alanlar belge ile dolduruldugu icin manuel duzenlemeye kapali.")

    assert page._survey_locked is True
    assert page.ent_anket_dersi_secen.state == "disabled"
    assert "manuel duzenlemeye kapali" in page.lbl_anket_kaynak_info.cget("text")


def test_preference_ratio_computed_correctly():
    page = CriteriaPage.__new__(CriteriaPage)
    page._survey_locked = True
    page.ent_toplam_ogrenci = _DummyEntry("200")
    page.ent_gecen_ogrenci = _DummyEntry("150")
    page.ent_ortalama = _DummyEntry("70")
    page.ent_kontenjan = _DummyEntry("220")
    page.ent_kayitli = _DummyEntry("0")
    page.ent_anket_katilimci = _DummyEntry("100", state="disabled")
    page.ent_anket_dersi_secen = _DummyEntry("25", state="disabled")
    page.lbl_basari_sonuc = _DummyLabel()
    page.lbl_doluluk_sonuc = _DummyLabel()
    page.lbl_anket_sonuc = _DummyLabel()

    page.update_calculations()

    assert page.ent_anket_katilimci.get() == "100"
    assert page.lbl_anket_sonuc.cget("text") == "%25.0"
