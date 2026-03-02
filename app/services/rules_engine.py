# app/services/rules_engine.py
# Kurallar Motoru: Engel, Kontenjan, Çakışma denetimleri

from app.services.calculation import ders_cakisma_kontrolu


def is_course_eligible_for_student(
    ogrenci_id: int,
    ders_id: int,
    secilen_dersler: list,
    db,
    yil: int = None,
) -> tuple:
    """
    Öğrencinin bir dersi alıp alamayacağını kurallara göre kontrol eder.

    Kurallar:
    1. Engel: Öğrenci bu dersten daha önce kendi isteğiyle kalmışsa (failed_before=True) -> red
    2. Kontenjan: Dersin kontenjanı dolmuşsa -> red
    3. Çakışma: Seçilen dersin gün/saati diğer seçilmiş derslerle çakışıyorsa -> red

    secilen_dersler: [(ders_id, gun, baslangic_saati, bitis_saati), ...]
    db: run_sql metodu olan nesne (örn. app.db)

    Döner: (gecerli: bool, sebep: str)
    """
    if db is None:
        return False, "Veritabanı bağlantısı yok"

    yil = yil or 2024

    # 1. Engel Denetimi (failed_before)
    try:
        _, rows = db.run_sql(
            "SELECT failed_before FROM kayit WHERE ogr_id = ? AND ders_id = ? LIMIT 1",
            (ogrenci_id, ders_id),
        )
        if rows and len(rows) > 0:
            failed = rows[0][0]
            if failed in (1, True, "1", "true", "True"):
                return False, "Engel: Öğrenci bu dersten daha önce kalmış (failed_before)"
    except Exception:
        # kayit tablosunda failed_before yoksa atla
        try:
            db.run_sql("SELECT 1 FROM kayit LIMIT 1")
        except Exception:
            pass

    # 2. Kontenjan Denetimi
    try:
        _, kont_rows = db.run_sql(
            """
            SELECT COALESCE(p.kontenjan, d.kontenjan, 999) as kont,
                   COALESCE(p.talep_sayisi, 0) as kayitli
            FROM ders d
            LEFT JOIN populerlik p ON d.ders_id = p.ders_id AND p.akademik_yil = ?
            WHERE d.ders_id = ?
            """,
            (yil, ders_id),
        )
        if kont_rows and len(kont_rows) > 0:
            kont = int(kont_rows[0][0] or 999)
            kayitli = int(kont_rows[0][1] or 0)
            if kont > 0 and kayitli >= kont:
                return False, "Kontenjan dolu"
    except Exception:
        # populerlik/ders yapısı farklı olabilir
        pass

    # 3. Çakışma Denetimi
    ders_saatleri = _get_ders_saatleri(db, ders_id)
    if ders_saatleri and secilen_dersler:
        tum_liste = list(secilen_dersler)
        for g, b, e in ders_saatleri:
            tum_liste.append((ders_id, g, b, e))
        cakisanlar = ders_cakisma_kontrolu(tum_liste)
        for (a, b) in cakisanlar:
            if a == ders_id or b == ders_id:
                return False, "Çakışma: Seçilen derslerle gün/saat çakışması"

    return True, "OK"


def _get_ders_saatleri(db, ders_id: int) -> list:
    """
    Dersin gün ve saat bilgilerini getirir.
    DersOgretim veya ders tablosundan.
    Döner: [(gun, baslangic_saati, bitis_saati), ...]
    """
    try:
        _, rows = db.run_sql(
            """
            SELECT gun, baslangic_saati, bitis_saati
            FROM ders_ogretim
            WHERE ders_id = ?
            """,
            (ders_id,),
        )
        if rows:
            return [tuple(r) for r in rows]
    except Exception:
        pass
    return []
