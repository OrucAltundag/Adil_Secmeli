# -*- coding: utf-8 -*-
"""Müfredat ders takası servisi.

Yeni üretilen bir müfredatta (bir `decision_run` çıktısı), önerilen/havuzdaki bir
ders ile müfredattaki herhangi bir ders TAKAS edilebilir:

    gelen ders (incoming)  ->  MUFREDATTA (final_status = 1)
    çıkan ders (outgoing)  ->  HAVUZDA    (final_status = 0)

Takas, hem karar çalıştırmasının müfredatını tutan `course_decisions` tablosuna
hem de canlı `mufredat_ders` ve `havuz.statu` tablolarına yansıtılır. Her takas
için `curriculum_swaps` tablosuna denetlenebilir bir kayıt yazılır.

Tasarım notu: Bu servis YENİDEN puanlama / yeniden TOPSIS yapmaz. Kullanıcının
açık (manuel) bir kararını uygular ve denetim için gerekçeyi saklar. Skorlar
değişmediği için, takas sonrası dersin kendi TOPSIS/açılabilirlik skoru aynen
korunur; yalnızca statü (müfredat/havuz) değişir.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from app.services.havuz_karar import STATU_HAVUZDA, STATU_MUFREDATTA


def ensure_swap_schema(conn: sqlite3.Connection) -> None:
    """`curriculum_swaps` denetim tablosunu (yoksa) oluşturur."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS curriculum_swaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER,
            year INTEGER,
            faculty_id INTEGER,
            department_id INTEGER,
            semester TEXT,
            incoming_course_id INTEGER NOT NULL,
            incoming_course_code TEXT,
            incoming_course_name TEXT,
            outgoing_course_id INTEGER NOT NULL,
            outgoing_course_code TEXT,
            outgoing_course_name TEXT,
            warnings_json TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL
        )
        """
    )


def _semester_initial(semester: str | None) -> str | None:
    s = (semester or "").strip()
    return s[0].upper() if s else None


def _course_meta(cur: sqlite3.Cursor, course_id: int) -> dict[str, Any] | None:
    cur.execute(
        "SELECT ders_id, kod, ad, kredi, akts, bolum_id, fakulte_id FROM ders WHERE ders_id = ?",
        (int(course_id),),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "ders_id": int(row[0]),
        "kod": row[1] or "",
        "ad": row[2] or "",
        "kredi": float(row[3]) if row[3] is not None else None,
        "akts": float(row[4]) if row[4] is not None else None,
        "bolum_id": int(row[5]) if row[5] is not None else None,
        "fakulte_id": int(row[6]) if row[6] is not None else None,
    }


def list_curriculum_courses_for_run(
    conn: sqlite3.Connection, run_id: int
) -> list[dict[str, Any]]:
    """Bir karar çalıştırmasında müfredatta (final_status=1) olan dersleri döndürür.

    Takas penceresinde "hangi dersle değiştireyim?" listesini besler.
    """
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cd.course_id, cd.final_status, cd.topsis_score, cd.acilabilirlik_score,
               d.kod AS kod, d.ad AS ad, d.kredi AS kredi, d.akts AS akts
        FROM course_decisions cd
        LEFT JOIN ders d ON d.ders_id = cd.course_id
        WHERE cd.decision_run_id = ? AND cd.final_status = ?
        ORDER BY d.ad
        """,
        (int(run_id), int(STATU_MUFREDATTA)),
    )
    out: list[dict[str, Any]] = []
    for r in cur.fetchall():
        out.append(
            {
                "ders_id": int(r["course_id"]),
                "kod": r["kod"] or "",
                "ad": r["ad"] or "",
                "kredi": float(r["kredi"]) if r["kredi"] is not None else None,
                "akts": float(r["akts"]) if r["akts"] is not None else None,
                "topsis_score": float(r["topsis_score"]) if r["topsis_score"] is not None else None,
                "acilabilirlik_score": float(r["acilabilirlik_score"]) if r["acilabilirlik_score"] is not None else None,
            }
        )
    return out


def _sync_havuz_statu(
    cur: sqlite3.Cursor,
    *,
    course_id: int,
    year: int,
    faculty_id: int | None,
    semester_initial: str | None,
    new_statu: int,
) -> int:
    """Canlı `havuz` tablosunda dersin statüsünü günceller. Etkilenen satır sayısını döndürür.

    havuz.ders_id metin olarak tutulduğundan CAST ile karşılaştırılır. Dönem,
    baş harf (G/B) ile eşleştirilir; böylece 'Guz'/'G' farkı sorun olmaz.
    """
    kosul = ["CAST(ders_id AS INTEGER) = ?", "yil = ?"]
    params: list[Any] = [int(course_id), int(year)]
    if faculty_id is not None:
        kosul.append("fakulte_id = ?")
        params.append(int(faculty_id))
    if semester_initial:
        kosul.append("UPPER(SUBSTR(TRIM(COALESCE(donem,'')),1,1)) = ?")
        params.append(semester_initial)
    cur.execute(
        f"UPDATE havuz SET statu = ?, final_status = ? WHERE {' AND '.join(kosul)}",
        [int(new_statu), int(new_statu), *params],
    )
    return cur.rowcount or 0


def _sync_mufredat_ders(
    cur: sqlite3.Cursor,
    *,
    incoming_course_id: int,
    outgoing_course_id: int,
    year: int,
    faculty_id: int | None,
    semester_initial: str | None,
) -> int:
    """Çıkan dersin bulunduğu müfredat satır(lar)ında ders_id'yi gelen ders ile değiştirir.

    Etkilenen `mufredat_ders` satır sayısını döndürür. Müfredat, fakülte/yıl ve
    dönem baş harfi ile kapsamlandırılır.
    """
    kosul = ["m.akademik_yil = ?"]
    params: list[Any] = [int(year)]
    if faculty_id is not None:
        kosul.append("m.fakulte_id = ?")
        params.append(int(faculty_id))
    if semester_initial:
        kosul.append("UPPER(SUBSTR(TRIM(COALESCE(m.donem,'')),1,1)) = ?")
        params.append(semester_initial)
    cur.execute(
        f"""
        SELECT md.mders_id
        FROM mufredat_ders md
        JOIN mufredat m ON m.mufredat_id = md.mufredat_id
        WHERE md.ders_id = ? AND {' AND '.join(kosul)}
        """,
        [int(outgoing_course_id), *params],
    )
    mders_ids = [int(r[0]) for r in cur.fetchall()]
    if not mders_ids:
        return 0
    placeholders = ",".join("?" * len(mders_ids))
    cur.execute(
        f"UPDATE mufredat_ders SET ders_id = ?, assignment_explanation = ? "
        f"WHERE mders_id IN ({placeholders})",
        [
            int(incoming_course_id),
            "Manuel takas ile müfredata eklendi",
            *mders_ids,
        ],
    )
    return cur.rowcount or 0


def swap_curriculum_course(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    incoming_course_id: int,
    outgoing_course_id: int,
    created_by: str | None = None,
) -> dict[str, Any]:
    """Önerilen bir dersi müfredattaki bir ders ile takas eder.

    Args:
        run_id: Karar çalıştırması (decision_run) kimliği.
        incoming_course_id: Müfredata GİRECEK (önerilen/havuz) ders.
        outgoing_course_id: Müfredattan ÇIKACAK ders.
        created_by: İşlemi yapan kullanıcı (denetim için).

    Returns:
        {"ok": bool, "error"?: str, "warnings": [...], "incoming": {...},
         "outgoing": {...}, "havuz_updated": int, "mufredat_updated": int}
    """
    if int(incoming_course_id) == int(outgoing_course_id):
        return {"ok": False, "error": "Aynı ders kendisiyle takas edilemez.", "warnings": []}

    from app.services.decision_run_service import get_decision_run

    ensure_swap_schema(conn)
    run = get_decision_run(conn, int(run_id))
    if not run:
        return {"ok": False, "error": f"Karar çalıştırması bulunamadı (run_id={run_id}).", "warnings": []}

    year = int(run.get("year"))
    faculty_id = run.get("faculty_id")
    faculty_id = int(faculty_id) if faculty_id is not None else None
    department_id = run.get("department_id")
    department_id = int(department_id) if department_id is not None else None
    semester = run.get("semester")
    sem_initial = _semester_initial(semester)

    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Bu run'daki karar kayıtlarını çek.
    cur.execute(
        "SELECT id, course_id, final_status FROM course_decisions WHERE decision_run_id = ?",
        (int(run_id),),
    )
    decisions = {int(r["course_id"]): {"id": int(r["id"]), "final_status": r["final_status"]} for r in cur.fetchall()}

    out_dec = decisions.get(int(outgoing_course_id))
    in_dec = decisions.get(int(incoming_course_id))

    if out_dec is None:
        return {"ok": False, "error": "Çıkacak ders bu karar çalıştırmasında bulunamadı.", "warnings": []}
    if out_dec["final_status"] is None or int(out_dec["final_status"]) != int(STATU_MUFREDATTA):
        return {"ok": False, "error": "Çıkacak ders şu an müfredatta değil; yalnızca müfredattaki bir ders çıkarılabilir.", "warnings": []}
    if in_dec is not None and in_dec["final_status"] is not None and int(in_dec["final_status"]) == int(STATU_MUFREDATTA):
        return {"ok": False, "error": "Gelecek ders zaten müfredatta.", "warnings": []}

    incoming_meta = _course_meta(cur, int(incoming_course_id))
    outgoing_meta = _course_meta(cur, int(outgoing_course_id))
    if incoming_meta is None or outgoing_meta is None:
        return {"ok": False, "error": "Ders bilgisi (ders tablosu) bulunamadı.", "warnings": []}

    # ── Uyarılar (engellemez, bilgilendirir) ──
    warnings: list[str] = []
    if incoming_meta["bolum_id"] != outgoing_meta["bolum_id"]:
        warnings.append(
            f"Bölüm farkı: gelen ders bölüm {incoming_meta['bolum_id']}, çıkan ders bölüm {outgoing_meta['bolum_id']}."
        )
    in_akts, out_akts = incoming_meta["akts"], outgoing_meta["akts"]
    if in_akts is not None and out_akts is not None and abs(in_akts - out_akts) > 0.001:
        warnings.append(f"AKTS farkı: gelen {in_akts:g} ↔ çıkan {out_akts:g}. Toplam AKTS değişebilir.")
    in_kredi, out_kredi = incoming_meta["kredi"], outgoing_meta["kredi"]
    if in_kredi is not None and out_kredi is not None and abs(in_kredi - out_kredi) > 0.001:
        warnings.append(f"Kredi farkı: gelen {in_kredi:g} ↔ çıkan {out_kredi:g}.")

    now = datetime.now().isoformat(timespec="seconds")
    in_reason = f"Manuel takas: {outgoing_meta['kod']} dersi ile değiştirildi (müfredata alındı)."
    out_reason = f"Manuel takas: {incoming_meta['kod']} dersi ile değiştirildi (havuza alındı)."

    try:
        # 1) Gelen ders -> MUFREDATTA. Eğer run'da kararı yoksa yeni satır oluştur.
        if in_dec is not None:
            cur.execute(
                "UPDATE course_decisions SET final_status = ?, override_applied = 1, "
                "override_reason = ?, main_reason = ? WHERE id = ?",
                (int(STATU_MUFREDATTA), in_reason, in_reason, int(in_dec["id"])),
            )
        else:
            cur.execute(
                """
                INSERT INTO course_decisions
                    (decision_run_id, course_id, year, faculty_id, department_id, semester,
                     old_status, recommended_status, final_status, override_applied,
                     override_reason, main_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    int(run_id), int(incoming_course_id), year, faculty_id, department_id, semester,
                    int(STATU_HAVUZDA), int(STATU_MUFREDATTA), int(STATU_MUFREDATTA),
                    in_reason, in_reason, now,
                ),
            )

        # 2) Çıkan ders -> HAVUZDA
        cur.execute(
            "UPDATE course_decisions SET final_status = ?, override_applied = 1, "
            "override_reason = ?, main_reason = ? WHERE id = ?",
            (int(STATU_HAVUZDA), out_reason, out_reason, int(out_dec["id"])),
        )

        # 3) Canlı havuz statüsünü senkronla
        havuz_updated = 0
        havuz_updated += _sync_havuz_statu(
            cur, course_id=int(incoming_course_id), year=year, faculty_id=faculty_id,
            semester_initial=sem_initial, new_statu=int(STATU_MUFREDATTA),
        )
        havuz_updated += _sync_havuz_statu(
            cur, course_id=int(outgoing_course_id), year=year, faculty_id=faculty_id,
            semester_initial=sem_initial, new_statu=int(STATU_HAVUZDA),
        )

        # 4) Canlı müfredat-ders bağını senkronla
        mufredat_updated = _sync_mufredat_ders(
            cur,
            incoming_course_id=int(incoming_course_id),
            outgoing_course_id=int(outgoing_course_id),
            year=year, faculty_id=faculty_id, semester_initial=sem_initial,
        )

        # 5) Denetim kaydı
        import json

        cur.execute(
            """
            INSERT INTO curriculum_swaps
                (decision_run_id, year, faculty_id, department_id, semester,
                 incoming_course_id, incoming_course_code, incoming_course_name,
                 outgoing_course_id, outgoing_course_code, outgoing_course_name,
                 warnings_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(run_id), year, faculty_id, department_id, semester,
                int(incoming_course_id), incoming_meta["kod"], incoming_meta["ad"],
                int(outgoing_course_id), outgoing_meta["kod"], outgoing_meta["ad"],
                json.dumps(warnings, ensure_ascii=False), created_by, now,
            ),
        )

        conn.commit()
    except Exception as exc:  # pragma: no cover - güvenlik ağı
        conn.rollback()
        return {"ok": False, "error": f"Takas uygulanamadı: {exc}", "warnings": warnings}

    return {
        "ok": True,
        "warnings": warnings,
        "incoming": incoming_meta,
        "outgoing": outgoing_meta,
        "havuz_updated": havuz_updated,
        "mufredat_updated": mufredat_updated,
        "run_id": int(run_id),
    }
