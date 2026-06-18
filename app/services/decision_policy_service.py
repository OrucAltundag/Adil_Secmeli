# -*- coding: utf-8 -*-
"""Decision policy resolution and threshold classification.

Karar politikasi servisi — iki ayri sorumlulugu yonetir:

1) **Politika yonetimi (CRUD + kapsam cozumu):**
   - `create_decision_policy` / `activate_decision_policy` / `deactivate_decision_policy`
   - `list_decision_policies` (saf okuma — CQS: yan etki uretmez)
   - `resolve_decision_policy` (department > faculty > global seklinde cozulur)

2) **TOPSIS skoru -> ders statusu cevrimi:**
   - `classify_score` — politikada tanimli esiklere gore statu uretir.

Sinif kuralilari (varsayilan esiklerle: cancel=30, rest=40, pool=50, keep=70):

| Skor araligi              | Statu        | Aciklama                                  |
|---------------------------|--------------|-------------------------------------------|
| score < cancel_threshold  | IPTAL ADAYI  | Manuel onay (policy'de tanimliysa)        |
| cancel <= score < pool    | DINLENMEDE   | rest altinda ise reason'da "derin" notu   |
| pool <= score < keep      | HAVUZDA      | Esik komsulugu icin hassas analiz onerilir|
| score >= keep             | MUFREDATTA   | Kararli sekilde tutulur                   |

NOT: rest_threshold artik sadece DINLENMEDE icinde "derin dinlenme" alt esigi
olarak kullaniliyor (statu degistirmez, yalnizca aciklamada belirir). Daha onceki
surumde 40-50 araligi yanlislikla HAVUZDA donuyordu — bu sessizce yanlis karar
uretimine yol aciyordu; iptal edildi.
"""

from __future__ import annotations

import math
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_decision_governance_schema
from app.services.havuz_karar import (
    STATU_DINLENMEDE,
    STATU_HAVUZDA,
    STATU_IPTAL,
    STATU_MUFREDATTA,
)

DEFAULT_POLICY = {
    "name": "Varsayilan Karar Politikasi",
    "scope_type": "global",
    "mode": "static_threshold",
    "curriculum_keep_threshold": 70.0,
    "pool_threshold": 50.0,
    "rest_threshold": 40.0,
    "cancel_candidate_threshold": 30.0,
    "new_course_grace_period_years": 2,
    "low_data_confidence_threshold": 0.50,
    "sensitivity_margin": 3.0,
    "require_manual_approval_for_cancel": True,
    "classification_method": "electre_tri_b",
    "electre_lambda": 0.65,
    "electre_assignment_rule": "pessimistic",
}

VALID_POLICY_MODES = {"static_threshold"}
VALID_SCOPE_TYPES = {"global", "faculty", "department"}


# ---------------------------------------------------------------------------
# Kucuk yardimcilar
# ---------------------------------------------------------------------------

def _now() -> str:
    # NOT: Format projedeki diger _now() helperlari ile ayni — string siralamasinin
    # bozulmamasi icin bilerek `YYYY-MM-DD HH:MM:SS` bicimde tutuldu.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return bool(value)


def _default_if_none(raw: Any, default: Any) -> Any:
    """`None` -> default. Diger truthy/falsy degerleri (ornegin 0) korur.

    Onceki surumde `value or default` kullanildigi icin DB'deki gercek 0
    degerleri sessizce default ile degistiriliyordu (P1 hata).
    """
    return default if raw is None else raw


def _json_value(raw: Any, default: Any) -> Any:
    if raw in (None, ""):
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _row_to_policy(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    # isinstance ile narrow yapıyoruz; Pylance'e Row vs tuple ayrımı net görünür.
    if isinstance(row, sqlite3.Row):
        keys: list[str] = list(row.keys())
    else:
        keys = []
    get = row.__getitem__

    def value(name: str, idx: int) -> Any:
        if keys and name in keys:
            return row[name]  # type: ignore[index]  # sqlite3.Row str index destekler
        return get(idx)

    cancel_raw = value("cancel_candidate_threshold", 10)
    policy = {
        "id": int(_default_if_none(value("id", 0), 0)),
        "name": str(_default_if_none(value("name", 1), "")),
        "scope_type": str(_default_if_none(value("scope_type", 2), "global")),
        "faculty_id": value("faculty_id", 3),
        "department_id": value("department_id", 4),
        "year": value("year", 5),
        "mode": str(_default_if_none(value("mode", 6), "static_threshold")),
        "curriculum_keep_threshold": float(_default_if_none(value("curriculum_keep_threshold", 7), 70.0)),
        "pool_threshold": float(_default_if_none(value("pool_threshold", 8), 50.0)),
        "rest_threshold": float(_default_if_none(value("rest_threshold", 9), 40.0)),
        "cancel_candidate_threshold": float(cancel_raw) if cancel_raw is not None else None,
        "min_success_rate": value("min_success_rate", 11),
        "min_survey_count": value("min_survey_count", 12),
        "min_enrollment_rate": value("min_enrollment_rate", 13),
        "new_course_grace_period_years": int(_default_if_none(value("new_course_grace_period_years", 14), 2)),
        "low_data_confidence_threshold": float(_default_if_none(value("low_data_confidence_threshold", 15), 0.50)),
        "sensitivity_margin": float(_default_if_none(value("sensitivity_margin", 16), 3.0)),
        "top_percent_curriculum": value("top_percent_curriculum", 17),
        "middle_percent_pool": value("middle_percent_pool", 18),
        "bottom_percent_rest": value("bottom_percent_rest", 19),
        "require_manual_approval_for_cancel": _bool(value("require_manual_approval_for_cancel", 20)),
        "is_active": _bool(value("is_active", 21)),
        "created_at": value("created_at", 22),
        "updated_at": value("updated_at", 23),
        "notes": value("notes", 24),
    }
    if keys:
        policy.update(
            {
                "classification_method": str(_default_if_none(value("classification_method", 25), "electre_tri_b")),
                "electre_lambda": float(_default_if_none(value("electre_lambda", 26), 0.65)),
                "electre_assignment_rule": str(_default_if_none(value("electre_assignment_rule", 27), "pessimistic")),
                "electre_q": _json_value(value("electre_q_json", 28), {}),
                "electre_p": _json_value(value("electre_p_json", 29), {}),
                "electre_veto": _json_value(value("electre_veto_json", 30), {}),
                "electre_profiles": _json_value(value("electre_profiles_json", 31), []),
            }
        )
    else:
        policy.update(
            {
                "classification_method": "electre_tri_b",
                "electre_lambda": 0.65,
                "electre_assignment_rule": "pessimistic",
                "electre_q": {},
                "electre_p": {},
                "electre_veto": {},
                "electre_profiles": [],
            }
        )
    return policy


def _deactivate_same_scope(
    cur: sqlite3.Cursor,
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int | None,
) -> None:
    cur.execute(
        """
        UPDATE decision_policies
        SET is_active = 0, updated_at = ?
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND COALESCE(year, -1) = COALESCE(?, -1)
        """,
        (_now(), str(scope_type or "global"), faculty_id, department_id, year),
    )


# ---------------------------------------------------------------------------
# Dogrulayicilar (validators)
# ---------------------------------------------------------------------------

def _validate_scope(
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
) -> None:
    if scope_type not in VALID_SCOPE_TYPES:
        raise ValueError(f"Gecersiz politika kapsami: {scope_type!r}")
    if scope_type == "global" and (faculty_id is not None or department_id is not None):
        raise ValueError("Global politika faculty_id veya department_id alamaz.")
    if scope_type == "faculty":
        if faculty_id is None:
            raise ValueError("Faculty politikasi icin faculty_id zorunludur.")
        if department_id is not None:
            raise ValueError("Faculty politikasi department_id alamaz.")
    if scope_type == "department" and (faculty_id is None or department_id is None):
        raise ValueError(
            "Department politikasi icin faculty_id ve department_id birlikte zorunludur."
        )


def validate_decision_policy_values(
    *,
    name: str,
    scope_type: str,
    mode: str,
    curriculum_keep_threshold: float,
    pool_threshold: float,
    rest_threshold: float,
    cancel_candidate_threshold: float | None,
    new_course_grace_period_years: int,
    low_data_confidence_threshold: float,
    sensitivity_margin: float,
    faculty_id: int | None = None,
    department_id: int | None = None,
    classification_method: str = "electre_tri_b",
    electre_lambda: float = 0.65,
    electre_assignment_rule: str = "pessimistic",
) -> None:
    """Politika alanlarinin iz kurallari acisindan tutarli oldugunu garanti eder.

    Hata bulundugunda `ValueError` firlatir. UI tarafindaki dogrulama disinda servis
    katmaninda da uygulanir; cunku servis baska girisli (API, script) cagrilirsa
    UI dogrulamasini atlatabilir.
    """
    if not str(name or "").strip():
        raise ValueError("Politika adi bos olamaz.")
    _validate_scope(scope_type, faculty_id, department_id)

    if mode not in VALID_POLICY_MODES:
        raise ValueError(
            f"Su anda yalnizca {sorted(VALID_POLICY_MODES)!r} modlari destekleniyor."
        )

    thresholds = [
        ("curriculum_keep_threshold", float(curriculum_keep_threshold)),
        ("pool_threshold", float(pool_threshold)),
        ("rest_threshold", float(rest_threshold)),
    ]
    if cancel_candidate_threshold is not None:
        thresholds.append(("cancel_candidate_threshold", float(cancel_candidate_threshold)))
    for key, val in thresholds:
        if not math.isfinite(val):
            raise ValueError(f"{key} sayisal ve sonlu olmalidir.")
        if val < 0 or val > 100:
            raise ValueError(f"{key} 0-100 araliginda olmalidir (gelen: {val}).")

    # Esik siralamasi: cancel <= rest < pool < curriculum_keep
    if cancel_candidate_threshold is not None:
        if not (
            float(cancel_candidate_threshold)
            <= float(rest_threshold)
            < float(pool_threshold)
            < float(curriculum_keep_threshold)
        ):
            raise ValueError(
                "Esikler su sirada olmalidir: iptal <= dinlenme < havuz < mufredat. "
                f"(gelen: iptal={cancel_candidate_threshold}, dinlenme={rest_threshold}, "
                f"havuz={pool_threshold}, mufredat={curriculum_keep_threshold})"
            )
    else:
        if not (float(rest_threshold) < float(pool_threshold) < float(curriculum_keep_threshold)):
            raise ValueError(
                "Esikler su sirada olmalidir: dinlenme < havuz < mufredat."
            )

    if int(new_course_grace_period_years) < 0:
        raise ValueError("Yeni ders koruma suresi negatif olamaz.")
    if not 0.0 <= float(low_data_confidence_threshold) <= 1.0:
        raise ValueError("Dusuk veri guveni esigi 0-1 araliginda olmalidir.")
    if float(sensitivity_margin) < 0:
        raise ValueError("Hassasiyet marji negatif olamaz.")
    if classification_method not in {"electre_tri_b", "static_threshold"}:
        raise ValueError("Siniflandirma yontemi electre_tri_b veya static_threshold olmalidir.")
    if not 0.50 <= float(electre_lambda) <= 1.0:
        raise ValueError("ELECTRE lambda degeri 0.50-1.00 araliginda olmalidir.")
    if electre_assignment_rule not in {"pessimistic"}:
        raise ValueError("Su anda yalnizca pessimistic ELECTRE atamasi destekleniyor.")


def _validate_score(score: float | None) -> float:
    """TOPSIS skorunun guvenli ve hesaplanabilir oldugunu dogrular.

    Karar sistemlerinde "skor yoktu ama 0 sayalim" davranisi sessiz hatalara
    yol acar (eksik veri = en kotu skor = iptal adayi sonucu). Bu yuzden
    `None`, `NaN`, sonsuz veya 0-100 araligi disindaki degerler reddedilir.
    """
    if score is None:
        raise ValueError(
            "TOPSIS skoru bos (None) olamaz. Eksik veriyi 0 olarak yorumlamayin; "
            "dersin skoru hesaplanamadiysa karar uretilmemelidir."
        )
    try:
        safe_score = float(score)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"TOPSIS skoru sayisal degil: {score!r}") from exc
    if not math.isfinite(safe_score):
        raise ValueError("TOPSIS skoru gecersiz: NaN veya sonsuz deger.")
    if safe_score < 0.0 or safe_score > 100.0:
        raise ValueError(f"TOPSIS skoru 0-100 araliginda olmalidir (gelen: {safe_score}).")
    return safe_score


# ---------------------------------------------------------------------------
# Politika CRUD + cozumu
# ---------------------------------------------------------------------------

def ensure_default_decision_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    """Global aktif bir politika oldugunu garanti eder. Mevcut aktif politikayi BOZMAZ.

    Onceki surumde yalnizca "Varsayilan Karar Politikasi" adli aktif kayit
    aranıyordu; kullanici farkli isimli ozel politikayi aktif yapinca, bu
    fonksiyon bunu gormezden gelip yeni bir varsayilan olusturarak kullanicinin
    politikasini sessizce pasifsiklestiriyordu (P0 hata).
    """
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1) Herhangi bir aktif global politika varsa, ona dokunma.
    cur.execute(
        """
        SELECT *
        FROM decision_policies
        WHERE scope_type = 'global'
          AND faculty_id IS NULL
          AND department_id IS NULL
          AND year IS NULL
          AND is_active = 1
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row:
        return _row_to_policy(row)

    # 2) Aktif yok ama varsayilan isimde pasif kayit varsa onu aktiflestir.
    cur.execute(
        """
        SELECT *
        FROM decision_policies
        WHERE scope_type = 'global'
          AND faculty_id IS NULL
          AND department_id IS NULL
          AND year IS NULL
          AND name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (DEFAULT_POLICY["name"],),
    )
    row = cur.fetchone()
    if row:
        policy = _row_to_policy(row)
        return activate_decision_policy(conn, policy["id"])

    # 3) Hicbir kayit yoksa yeni varsayilan olustur.
    return create_decision_policy(conn, **DEFAULT_POLICY, activate=True)


def create_decision_policy(
    conn: sqlite3.Connection,
    name: str,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    mode: str = "static_threshold",
    curriculum_keep_threshold: float = 70.0,
    pool_threshold: float = 50.0,
    rest_threshold: float = 40.0,
    cancel_candidate_threshold: float | None = 30.0,
    min_success_rate: float | None = None,
    min_survey_count: int | None = None,
    min_enrollment_rate: float | None = None,
    new_course_grace_period_years: int = 2,
    low_data_confidence_threshold: float = 0.50,
    sensitivity_margin: float = 3.0,
    top_percent_curriculum: float | None = None,
    middle_percent_pool: float | None = None,
    bottom_percent_rest: float | None = None,
    require_manual_approval_for_cancel: bool = True,
    classification_method: str = "electre_tri_b",
    electre_lambda: float = 0.65,
    electre_assignment_rule: str = "pessimistic",
    electre_q: dict[str, float] | None = None,
    electre_p: dict[str, float] | None = None,
    electre_veto: dict[str, float | None] | None = None,
    electre_profiles: list[dict[str, Any]] | None = None,
    notes: str | None = None,
    activate: bool = True,
) -> dict[str, Any]:
    ensure_decision_governance_schema(conn, commit=False)

    # DB'ye yazmadan once is kurallari dogrulansin (P0/P1 onlem).
    validate_decision_policy_values(
        name=name,
        scope_type=scope_type,
        mode=mode,
        curriculum_keep_threshold=curriculum_keep_threshold,
        pool_threshold=pool_threshold,
        rest_threshold=rest_threshold,
        cancel_candidate_threshold=cancel_candidate_threshold,
        new_course_grace_period_years=new_course_grace_period_years,
        low_data_confidence_threshold=low_data_confidence_threshold,
        sensitivity_margin=sensitivity_margin,
        faculty_id=faculty_id,
        department_id=department_id,
        classification_method=classification_method,
        electre_lambda=electre_lambda,
        electre_assignment_rule=electre_assignment_rule,
    )

    cur = conn.cursor()
    if activate:
        _deactivate_same_scope(cur, scope_type, faculty_id, department_id, year)
    cur.execute(
        """
        INSERT INTO decision_policies (
            name, scope_type, faculty_id, department_id, year, mode,
            curriculum_keep_threshold, pool_threshold, rest_threshold,
            cancel_candidate_threshold, min_success_rate, min_survey_count,
            min_enrollment_rate, new_course_grace_period_years,
            low_data_confidence_threshold, sensitivity_margin,
            top_percent_curriculum, middle_percent_pool, bottom_percent_rest,
            require_manual_approval_for_cancel, classification_method, electre_lambda,
            electre_assignment_rule, electre_q_json, electre_p_json, electre_veto_json,
            electre_profiles_json, is_active, created_at, updated_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(name),
            str(scope_type or "global"),
            faculty_id,
            department_id,
            year,
            str(mode or "static_threshold"),
            float(curriculum_keep_threshold),
            float(pool_threshold),
            float(rest_threshold),
            cancel_candidate_threshold,
            min_success_rate,
            min_survey_count,
            min_enrollment_rate,
            int(new_course_grace_period_years),
            float(low_data_confidence_threshold),
            float(sensitivity_margin),
            top_percent_curriculum,
            middle_percent_pool,
            bottom_percent_rest,
            1 if require_manual_approval_for_cancel else 0,
            str(classification_method),
            float(electre_lambda),
            str(electre_assignment_rule),
            json.dumps(electre_q or {}, ensure_ascii=False, sort_keys=True),
            json.dumps(electre_p or {}, ensure_ascii=False, sort_keys=True),
            json.dumps(electre_veto or {}, ensure_ascii=False, sort_keys=True),
            json.dumps(electre_profiles or [], ensure_ascii=False, sort_keys=True),
            1 if activate else 0,
            _now(),
            _now(),
            notes,
        ),
    )
    policy_id = int(cur.lastrowid or 0)
    conn.commit()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (policy_id,))
    return _row_to_policy(cur.fetchone())


def resolve_decision_policy(
    conn: sqlite3.Connection,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    """Karar calistirmasinda kullanilacak en spesifik aktif politikayi bulur.

    Sirayla: department(yil) > faculty(yil) > department > faculty > global(yil) > global.
    Hicbiri yoksa varsayilan global olusturulur.
    """
    ensure_default_decision_policy(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    candidates = [
        ("department", faculty_id, department_id, year),
        ("faculty", faculty_id, None, year),
        ("department", faculty_id, department_id, None),
        ("faculty", faculty_id, None, None),
        ("global", None, None, year),
        ("global", None, None, None),
    ]
    for scope_type, fac_id, dep_id, policy_year in candidates:
        if scope_type == "department" and dep_id is None:
            continue
        if scope_type == "faculty" and fac_id is None:
            continue
        cur.execute(
            """
            SELECT *
            FROM decision_policies
            WHERE is_active = 1
              AND scope_type = ?
              AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
              AND COALESCE(department_id, -1) = COALESCE(?, -1)
              AND COALESCE(year, -1) = COALESCE(?, -1)
            ORDER BY id DESC
            LIMIT 1
            """,
            (scope_type, fac_id, dep_id, policy_year),
        )
        row = cur.fetchone()
        if row:
            return _row_to_policy(row)
    return ensure_default_decision_policy(conn)


def list_decision_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Politikalari yalnizca okur — yan etki uretmez (CQS: Command/Query Separation).

    Onceki surum, listeleme sirasinda `ensure_default_decision_policy` cagirir,
    bu da kullanicinin aktif politikasini pasiflestirebilirdi. Boyle bir
    "okuma yapayim derken yazi yazma" davranisi servis acisindan tehlikeli.
    Sema kontrolu zararsiz oldugu icin tutuldu; varsayilan politika olusumu ise
    yalnizca acik yazma yollarina (resolve / create / activate / ensure) birakildi.
    """
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM decision_policies ORDER BY is_active DESC, scope_type, year DESC, id DESC"
    )
    return [_row_to_policy(row) for row in cur.fetchall()]


def activate_decision_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]:
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Karar politikasi bulunamadi: {policy_id}")
    policy = _row_to_policy(row)
    _deactivate_same_scope(
        cur,
        policy["scope_type"],
        policy["faculty_id"],
        policy["department_id"],
        policy["year"],
    )
    cur.execute(
        "UPDATE decision_policies SET is_active = 1, updated_at = ? WHERE id = ?",
        (_now(), int(policy_id)),
    )
    conn.commit()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    return _row_to_policy(cur.fetchone())


def update_decision_policy(conn: sqlite3.Connection, policy_id: int, **values: Any) -> dict[str, Any]:
    """Mevcut karar politikasini servis kurallariyla dogrulayarak gunceller."""
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Karar politikasi bulunamadi: {policy_id}")

    current = _row_to_policy(row)
    allowed = {
        "name",
        "scope_type",
        "faculty_id",
        "department_id",
        "year",
        "mode",
        "curriculum_keep_threshold",
        "pool_threshold",
        "rest_threshold",
        "cancel_candidate_threshold",
        "min_success_rate",
        "min_survey_count",
        "min_enrollment_rate",
        "new_course_grace_period_years",
        "low_data_confidence_threshold",
        "sensitivity_margin",
        "top_percent_curriculum",
        "middle_percent_pool",
        "bottom_percent_rest",
        "require_manual_approval_for_cancel",
        "classification_method",
        "electre_lambda",
        "electre_assignment_rule",
        "electre_q",
        "electre_p",
        "electre_veto",
        "electre_profiles",
        "notes",
    }
    updates = {key: value for key, value in values.items() if key in allowed}
    if not updates:
        return current

    merged = dict(current)
    merged.update(updates)

    validate_decision_policy_values(
        name=str(merged.get("name") or ""),
        scope_type=str(merged.get("scope_type") or "global"),
        mode=str(merged.get("mode") or "static_threshold"),
        curriculum_keep_threshold=float(merged.get("curriculum_keep_threshold") or 0),
        pool_threshold=float(merged.get("pool_threshold") or 0),
        rest_threshold=float(merged.get("rest_threshold") or 0),
        cancel_candidate_threshold=(
            None
            if merged.get("cancel_candidate_threshold") is None
            else float(merged.get("cancel_candidate_threshold") or 0.0)
        ),
        new_course_grace_period_years=int(merged.get("new_course_grace_period_years") or 0),
        low_data_confidence_threshold=float(merged.get("low_data_confidence_threshold") or 0),
        sensitivity_margin=float(merged.get("sensitivity_margin") or 0),
        faculty_id=merged.get("faculty_id"),
        department_id=merged.get("department_id"),
        classification_method=str(merged.get("classification_method") or "electre_tri_b"),
        electre_lambda=float(merged.get("electre_lambda") or 0.65),
        electre_assignment_rule=str(merged.get("electre_assignment_rule") or "pessimistic"),
    )

    if "name" in updates:
        updates["name"] = str(updates["name"] or "").strip()
    if "mode" in updates:
        updates["mode"] = str(updates["mode"] or "static_threshold")
    if "scope_type" in updates:
        updates["scope_type"] = str(updates["scope_type"] or "global")
    if "require_manual_approval_for_cancel" in updates:
        updates["require_manual_approval_for_cancel"] = (
            1 if _bool(updates["require_manual_approval_for_cancel"]) else 0
        )
    for public_key, column_name in (
        ("electre_q", "electre_q_json"),
        ("electre_p", "electre_p_json"),
        ("electre_veto", "electre_veto_json"),
        ("electre_profiles", "electre_profiles_json"),
    ):
        if public_key in updates:
            updates[column_name] = json.dumps(
                updates.pop(public_key) or ({} if public_key != "electre_profiles" else []),
                ensure_ascii=False,
                sort_keys=True,
            )

    assignments = ", ".join(f"{key} = ?" for key in updates)
    params = list(updates.values()) + [_now(), int(policy_id)]
    cur.execute(
        f"UPDATE decision_policies SET {assignments}, updated_at = ? WHERE id = ?",
        params,
    )
    conn.commit()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    return _row_to_policy(cur.fetchone())


def deactivate_decision_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]:
    """Bir politikayi pasiflestirir. Ayni kapsamda baska aktif politika brakmaz;
    UI/cagrian taraf gerekirse yeni bir politika aktiflestirmelidir."""
    ensure_decision_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Karar politikasi bulunamadi: {policy_id}")
    cur.execute(
        "UPDATE decision_policies SET is_active = 0, updated_at = ? WHERE id = ?",
        (_now(), int(policy_id)),
    )
    conn.commit()
    cur.execute("SELECT * FROM decision_policies WHERE id = ?", (int(policy_id),))
    return _row_to_policy(cur.fetchone())


# ---------------------------------------------------------------------------
# Skor -> statu donusumu
# ---------------------------------------------------------------------------

def classify_score(score: float | None, policy: dict[str, Any]) -> dict[str, Any]:
    """TOPSIS skorunu politika esiklerine gore karar dict'ine donusturur.

    Returns:
        dict: en az asagidaki anahtarlari icerir (geri uyumlu):
            - recommended_status (int)
            - rule_triggered (str)
            - reason (str)
        Eklenen yeni alanlar (additive):
            - score (float)
            - requires_manual_approval (bool)
            - severity (str: "info" | "warning" | "critical")
            - thresholds (dict): degerlendirmede kullanilan esikler

    Raises:
        ValueError: skor None / NaN / sonsuz / 0-100 araligi disinda ise.
    """
    safe_score = _validate_score(score)

    # Su an yalnizca static_threshold destekleniyor; ileride yuzdelik mod eklenecekse
    # buradan dispatch yapilabilir. Bilinmeyen mod gelirse acik hata verilir.
    mode = str(policy.get("mode") or "static_threshold")
    if mode != "static_threshold":
        raise ValueError(
            f"Desteklenmeyen politika modu: {mode!r}. "
            f"Su an yalnizca {sorted(VALID_POLICY_MODES)!r} destekleniyor."
        )

    cancel_t = policy.get("cancel_candidate_threshold")
    rest_t = float(policy.get("rest_threshold", 40.0))
    pool_t = float(policy.get("pool_threshold", 50.0))
    keep_t = float(policy.get("curriculum_keep_threshold", 70.0))
    sensitivity_margin = float(policy.get("sensitivity_margin", 3.0) or 0.0)
    require_manual_cancel = _bool(policy.get("require_manual_approval_for_cancel", True))

    thresholds_used = {
        "cancel_candidate_threshold": float(cancel_t) if cancel_t is not None else None,
        "rest_threshold": rest_t,
        "pool_threshold": pool_t,
        "curriculum_keep_threshold": keep_t,
    }

    base = {
        "score": safe_score,
        "thresholds": thresholds_used,
        "requires_manual_approval": False,
    }

    # 1) IPTAL ADAYI — yalnizca politikada cancel_threshold acikca tanimliysa.
    if cancel_t is not None and safe_score < float(cancel_t):
        return {
            **base,
            "recommended_status": STATU_IPTAL,
            "rule_triggered": "cancel_candidate_threshold",
            "requires_manual_approval": require_manual_cancel,
            "severity": "critical",
            "reason": (
                f"Skor {safe_score:.1f}, iptal adayi esiginin ({float(cancel_t):.1f}) altinda."
            ),
        }

    # 2) DINLENMEDE — havuz esigi altindaki tum skorlar.
    if safe_score < pool_t:
        deep = safe_score < rest_t
        rule = "rest_threshold" if deep else "pool_threshold"
        note = " (rest esiginin altinda — derin dinlenme)" if deep else ""
        return {
            **base,
            "recommended_status": STATU_DINLENMEDE,
            "rule_triggered": rule,
            "severity": "warning",
            "reason": (
                f"Skor {safe_score:.1f}, havuz esiginin ({pool_t:.1f}) altinda{note}."
            ),
        }

    # 3) HAVUZDA — mufredatta kalmaya yetmiyor.
    if safe_score < keep_t:
        # Esige cok yakinsa downstream icin uyari isareti olarak severity yukseltilir.
        sensitive = abs(safe_score - keep_t) <= sensitivity_margin or abs(safe_score - pool_t) <= sensitivity_margin
        return {
            **base,
            "recommended_status": STATU_HAVUZDA,
            "rule_triggered": "curriculum_keep_threshold",
            "severity": "warning" if sensitive else "info",
            "reason": (
                f"Skor {safe_score:.1f}, mufredatta kalma esiginin ({keep_t:.1f}) altinda."
            ),
        }

    # 4) MUFREDATTA — esik karsilaniyor.
    sensitive = abs(safe_score - keep_t) <= sensitivity_margin
    return {
        **base,
        "recommended_status": STATU_MUFREDATTA,
        "rule_triggered": "curriculum_keep_threshold",
        "severity": "warning" if sensitive else "info",
        "reason": (
            f"Skor {safe_score:.1f}, mufredatta kalma esigini ({keep_t:.1f}) karsiliyor."
        ),
    }


def status_label(status: int | None) -> str:
    """Kullanici arayuzunde gosterilecek Turkce statu etiketi."""
    labels = {
        STATU_MUFREDATTA: "Müfredatta",
        STATU_HAVUZDA: "Havuzda",
        STATU_DINLENMEDE: "Dinlenmede",
        STATU_IPTAL: "İptal Adayı",
    }
    if status is None:
        return "Belirsiz"
    try:
        return labels.get(int(status), "Belirsiz")
    except (TypeError, ValueError):
        return "Belirsiz"
