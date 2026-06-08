# -*- coding: utf-8 -*-
"""Kriter tamlık politikası çözümleme servisi.

Bu servis "hangi tamlık politikası geçerli?" sorusunu çözer. Politika katmanı
sistemin güvenlik anayasası gibidir; bu yüzden burada *sessiz* hataya yer yoktur:
geçersiz kapsam, geçersiz dönem veya tutarsız ID kombinasyonları otomatik
"düzeltilmez", açıkça `ValueError` ile reddedilir.

Transaction sözleşmesi
----------------------
Yazma yapan fonksiyonlar (`create_default_policy`, `create_completion_policy`,
`activate_completion_policy`) `commit` parametresi alır:

* ``commit=True``  (varsayılan): Fonksiyon kendi işlemini atomik olarak commit
  eder; hata durumunda rollback yapar.
* ``commit=False``: Değişiklikler açık transaction içinde bırakılır, commit/rollback
  sorumluluğu *çağıran katmana* aittir. `resolve_policy` salt-okuma yolundayken
  varsayılan politikayı bu modda üretir; böylece okuma sırasında istenmeyen bir
  commit yan etkisi oluşmaz (bkz. docs/criteria_completion_governance.md §11).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema

logger = logging.getLogger(__name__)

# Kriter Tamlık Yönetişimi belgesiyle uyumlu varsayılan alan tanımları
DEFAULT_REQUIRED_FIELDS = [
    "total_students",
    "passed_students",
    "average_grade",
    "capacity",
    "enrolled_students",
]
DEFAULT_OPTIONAL_FIELDS = ["survey_count", "trend"]

# Politikalarda kullanılabilecek geçerli kriter alanları (whitelist).
VALID_CRITERIA_FIELDS = {
    "total_students",
    "passed_students",
    "average_grade",
    "capacity",
    "enrolled_students",
    "survey_count",
    "trend",
}

VALID_SCOPE_TYPES = {"global", "faculty", "department"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_semester(value: str | None) -> str | None:
    """Dönem değerini 'Güz'/'Bahar' kanonik biçimine indirger.

    Bilinmeyen bir değer sessizce 'Güz' yapılmaz; açıkça reddedilir. Böylece
    'Yaz' gibi geçersiz bir girdi yanlış bir politikanın çözülmesine yol açmaz.
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw:
        return None
    mapping = {
        "b": "Bahar",
        "bahar": "Bahar",
        "spring": "Bahar",
        "s": "Bahar",
        "g": "Güz",
        "güz": "Güz",
        "guz": "Güz",
        "fall": "Güz",
        "autumn": "Güz",
    }
    if raw in mapping:
        return mapping[raw]
    raise ValueError(
        f"Geçersiz dönem (semester) değeri: '{value}'. Sadece 'Güz' veya 'Bahar' kabul edilir."
    )


def _to_bool(value: Any) -> bool:
    """SQLite/JSON kaynaklı değerleri güvenli biçimde bool'a çevirir.

    `bool("0")` Python'da True döndürdüğü için string değerler özel ele alınır.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "evet"}
    return bool(value)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None, default: Any) -> Any:
    """JSON çözer; bozuk veriyi sessizce yutmaz, en azından loglar."""
    if not value:
        return list(default) if isinstance(default, list) else default
    try:
        return json.loads(value)
    except Exception:
        logger.exception(
            "Politika JSON alanı ayrıştırılamadı, varsayılan değere düşülüyor. Ham veri: %r",
            value,
        )
        return list(default) if isinstance(default, list) else default


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        data = {columns[idx]: row[idx] for idx in range(min(len(columns or []), len(row)))} if columns else {}
    data["required_fields"] = _json_loads(data.get("required_fields_json"), DEFAULT_REQUIRED_FIELDS)
    data["optional_fields"] = _json_loads(data.get("optional_fields_json"), DEFAULT_OPTIONAL_FIELDS)
    for key in (
        "allow_new_course_missing_history",
        "block_on_invalid_numeric",
        "block_on_critical_issues",
        "allow_override",
        "override_requires_reason",
        "override_requires_approval",
        "is_active",
    ):
        if key in data:
            data[key] = _to_bool(data.get(key))
    return data


# ---------------------------------------------------------------------------
# Doğrulama yardımcıları
# ---------------------------------------------------------------------------


def _validate_scope_and_ids(
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    *,
    strict: bool = True,
) -> tuple[str, int | None, int | None]:
    """Kapsam tipi ile ID alanlarının tutarlılığını uygular (Kapsam İzolasyonu).

    `strict=True` (yazma yolu): fazladan dolu gelen ID'ler `ValueError` ile
    reddedilir; böylece erişilemez/anlamsız politika kaydı oluşmaz.

    `strict=False` (okuma/çözümleme yolu): kapsama göre ilgisiz ID'ler sessizce
    NULL'a indirgenir (örn. faculty kapsamında gelen department_id yok sayılır).
    Yalnızca *zorunlu* ID eksikse hata verilir; çünkü bu gerçek bir programlama
    hatasıdır ve güvenlik kapısını yanlış politikayla geçirmemek gerekir.
    """
    scope = str(scope_type or "").strip().lower()
    if scope not in VALID_SCOPE_TYPES:
        raise ValueError(
            f"Geçersiz politika kapsamı (scope_type): '{scope_type}'. "
            f"Geçerli tipler: {sorted(VALID_SCOPE_TYPES)}"
        )
    if scope == "global":
        if strict and (faculty_id is not None or department_id is not None):
            raise ValueError("Global politika için faculty_id ve department_id NULL olmalıdır.")
        return scope, None, None
    if scope == "faculty":
        if faculty_id is None:
            raise ValueError("Fakülte kapsamındaki politika için faculty_id zorunludur.")
        if strict and department_id is not None:
            raise ValueError("Fakülte kapsamındaki politika için department_id NULL olmalıdır.")
        return scope, int(faculty_id), None
    # scope == "department"
    if faculty_id is None or department_id is None:
        raise ValueError("Bölüm kapsamındaki politika için faculty_id ve department_id zorunludur.")
    return scope, int(faculty_id), int(department_id)


def _normalize_field_list(value: list[str] | None, default: list[str], label: str) -> list[str]:
    """Kriter alan listesini doğrular: geçerli alan adı, tekilleştirme, sıra korunur.

    ``value is None`` ise varsayılan listeye düşülür. ``value == []`` ise boş liste
    *korunur* (kasıtlı 'zorunlu alan yok' senaryosu sessizce ezilmez)."""
    fields = default if value is None else value
    if not isinstance(fields, list):
        raise ValueError(f"'{label}' bir string listesi olmalıdır.")
    cleaned: list[str] = []
    for item in fields:
        field = str(item).strip()
        if not field:
            continue
        if field not in VALID_CRITERIA_FIELDS:
            raise ValueError(
                f"'{label}' listesinde geçersiz kriter alanı: '{field}'. "
                f"Geçerli alanlar: {sorted(VALID_CRITERIA_FIELDS)}"
            )
        if field not in cleaned:
            cleaned.append(field)
    return cleaned


def _validate_policy_fields(
    required_fields: list[str] | None,
    optional_fields: list[str] | None,
) -> tuple[list[str], list[str]]:
    """Zorunlu/opsiyonel alan listelerini doğrular ve çakışmayı engeller.

    Aynı alanın hem zorunlu hem opsiyonel olması (örn. `trend`) matriste ve UI'da
    çelişki üretir; bu yüzden açıkça reddedilir.
    """
    required = _normalize_field_list(required_fields, DEFAULT_REQUIRED_FIELDS, "required_fields")
    optional = _normalize_field_list(optional_fields, DEFAULT_OPTIONAL_FIELDS, "optional_fields")
    overlap = set(required) & set(optional)
    if overlap:
        raise ValueError(
            f"Bir kriter alanı aynı anda hem zorunlu hem opsiyonel olamaz: {sorted(overlap)}"
        )
    return required, optional


# ---------------------------------------------------------------------------
# Politika CRUD
# ---------------------------------------------------------------------------


def create_default_policy(conn: sqlite3.Connection, commit: bool = True) -> dict[str, Any]:
    """Aktif bir global varsayılan politika yoksa oluşturur.

    Zaten varsa onu döndürür (yazma yapmaz). `commit` davranışı için modül
    docstring'indeki transaction sözleşmesine bakın.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM criteria_completion_policies
        WHERE scope_type = 'global' AND is_active = 1
          AND faculty_id IS NULL AND department_id IS NULL
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row:
        return _row_to_dict(row) or {}
    now = _now()
    try:
        cur.execute(
            """
            INSERT INTO criteria_completion_policies (
                name, scope_type, required_completion_ratio, required_fields_json,
                optional_fields_json, allow_new_course_missing_history,
                new_course_grace_period_years, block_on_invalid_numeric,
                block_on_critical_issues, allow_override, override_requires_reason,
                override_requires_approval, is_active, created_at, updated_at, notes
            )
            VALUES (?, 'global', 1.0, ?, ?, 1, 2, 1, 1, 1, 1, 1, 1, ?, ?, ?)
            """,
            (
                "Varsayılan Kriter Tamlık Politikası",
                _json_dumps(DEFAULT_REQUIRED_FIELDS),
                _json_dumps(DEFAULT_OPTIONAL_FIELDS),
                now,
                now,
                "Geriye dönük güvenlik için zorunlu alanlarda %100 tamlık ister.",
            ),
        )
        last_id = int(cur.lastrowid or 0)
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()
    return get_policy(conn, last_id) or {}


def get_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM criteria_completion_policies WHERE id = ?", (int(policy_id),))
    return _row_to_dict(cur.fetchone())


def create_completion_policy(
    conn: sqlite3.Connection,
    name: str,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    required_completion_ratio: float = 1.0,
    required_fields: list[str] | None = None,
    optional_fields: list[str] | None = None,
    allow_new_course_missing_history: bool = True,
    new_course_grace_period_years: int = 2,
    min_survey_response_count: int | None = None,
    block_on_invalid_numeric: bool = True,
    block_on_critical_issues: bool = True,
    allow_override: bool = True,
    override_requires_reason: bool = True,
    override_requires_approval: bool = True,
    notes: str | None = None,
    activate: bool = True,
    commit: bool = True,
) -> dict[str, Any]:
    """Yeni bir tamlık politikası doğrulanmış kurallarla ekler.

    `activate=True` ise aynı kapsamdaki eski aktif politikalar aynı transaction
    içinde pasifleştirilir (atomik).
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)

    # --- Giriş doğrulamaları (sessiz düzeltme yok, açık reddetme var) ---
    if not str(name or "").strip():
        raise ValueError("Politika adı (name) boş olamaz.")
    scope_type, faculty_id, department_id = _validate_scope_and_ids(scope_type, faculty_id, department_id)
    semester = _normalize_semester(semester)
    required_fields, optional_fields = _validate_policy_fields(required_fields, optional_fields)
    if not (0.0 <= float(required_completion_ratio) <= 1.0):
        raise ValueError(
            f"required_completion_ratio 0.0 ile 1.0 arasında olmalıdır. Girilen: {required_completion_ratio}"
        )
    if int(new_course_grace_period_years) < 0:
        raise ValueError("new_course_grace_period_years değeri negatif olamaz.")
    if min_survey_response_count is not None and int(min_survey_response_count) < 0:
        raise ValueError("min_survey_response_count değeri negatif olamaz.")

    now = _now()
    cur = conn.cursor()
    try:
        if activate:
            where = ["scope_type = ?"]
            params: list[Any] = [scope_type]
            for col, value in (
                ("faculty_id", faculty_id),
                ("department_id", department_id),
                ("year", year),
                ("semester", semester),
            ):
                if value is None:
                    where.append(f"{col} IS NULL")
                else:
                    where.append(f"{col} = ?")
                    params.append(value)
            cur.execute(
                f"UPDATE criteria_completion_policies SET is_active = 0, updated_at = ? WHERE {' AND '.join(where)}",
                tuple([now] + params),
            )
        cur.execute(
            """
            INSERT INTO criteria_completion_policies (
                name, scope_type, faculty_id, department_id, year, semester,
                required_completion_ratio, required_fields_json, optional_fields_json,
                allow_new_course_missing_history, new_course_grace_period_years,
                min_survey_response_count, block_on_invalid_numeric, block_on_critical_issues,
                allow_override, override_requires_reason, override_requires_approval,
                is_active, created_at, updated_at, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(name).strip(),
                scope_type,
                faculty_id,
                department_id,
                None if year is None else int(year),
                semester,
                float(required_completion_ratio),
                _json_dumps(required_fields),
                _json_dumps(optional_fields),
                1 if allow_new_course_missing_history else 0,
                int(new_course_grace_period_years),
                int(min_survey_response_count) if min_survey_response_count is not None else None,
                1 if block_on_invalid_numeric else 0,
                1 if block_on_critical_issues else 0,
                1 if allow_override else 0,
                1 if override_requires_reason else 0,
                1 if override_requires_approval else 0,
                1 if activate else 0,
                now,
                now,
                notes,
            ),
        )
        last_id = int(cur.lastrowid or 0)
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()
    return get_policy(conn, last_id) or {}


def resolve_policy(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    """Seçili kapsama göre en uygun aktif tamlık politikasını hiyerarşik çözer.

    Kapsam İzolasyonu: `scope_type="faculty"` iken bölüm politikaları aranmaz;
    aday listesi parametredeki `scope_type` değerine göre kurulur. Böylece yanlışlıkla
    dolu gelmiş bir `department_id`, fakülte kapsamında bölüm politikasını uygulamaz.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    # Okuma yolu: ilgisiz ID'ler kapsama göre NULL'a indirgenir (kanma yok), reddetme yok.
    scope_type, faculty_id, department_id = _validate_scope_and_ids(
        scope_type, faculty_id, department_id, strict=False
    )
    semester = _normalize_semester(semester)

    candidates: list[tuple[str, int | None, int | None, int | None, str | None]] = []
    if scope_type == "department":
        candidates.extend(
            [
                ("department", faculty_id, department_id, year, semester),
                ("department", faculty_id, department_id, year, None),
                ("faculty", faculty_id, None, year, semester),
                ("faculty", faculty_id, None, year, None),
                ("department", faculty_id, department_id, None, None),
                ("faculty", faculty_id, None, None, None),
            ]
        )
    elif scope_type == "faculty":
        candidates.extend(
            [
                ("faculty", faculty_id, None, year, semester),
                ("faculty", faculty_id, None, year, None),
                ("faculty", faculty_id, None, None, None),
            ]
        )
    # Global katman her zaman son koruma bariyeri olarak eklenir.
    candidates.extend(
        [
            ("global", None, None, year, None),
            ("global", None, None, None, None),
        ]
    )

    cur = conn.cursor()
    for cand_scope, cand_faculty, cand_department, cand_year, cand_semester in candidates:
        where = ["scope_type = ?", "is_active = 1"]
        params: list[Any] = [cand_scope]
        for col, value in (
            ("faculty_id", cand_faculty),
            ("department_id", cand_department),
            ("year", cand_year),
            ("semester", cand_semester),
        ):
            if value is None:
                where.append(f"{col} IS NULL")
            else:
                where.append(f"{col} = ?")
                params.append(value)
        cur.execute(
            f"SELECT * FROM criteria_completion_policies WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
            tuple(params),
        )
        row = cur.fetchone()
        if row:
            return _row_to_dict(row) or {}

    # Hiç eşleşme yoksa: varsayılan politikayı salt-okuma yolunda commit etmeden üret.
    return create_default_policy(conn, commit=False)


def list_completion_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM criteria_completion_policies ORDER BY is_active DESC, id DESC")
    return [_row_to_dict(row) or {} for row in cur.fetchall()]


def activate_completion_policy(conn: sqlite3.Connection, policy_id: int, commit: bool = True) -> dict[str, Any]:
    """Bir politikayı aktif yapar ve aynı kapsamdaki diğerlerini atomik olarak kapatır."""
    policy = get_policy(conn, policy_id)
    if not policy:
        raise ValueError(f"Aktivasyon hatası: {policy_id} ID'li kriter tamlık politikası bulunamadı.")
    now = _now()
    cur = conn.cursor()
    where = ["scope_type = ?"]
    params: list[Any] = [policy["scope_type"]]
    for col in ("faculty_id", "department_id", "year", "semester"):
        value = policy.get(col)
        if value is None:
            where.append(f"{col} IS NULL")
        else:
            where.append(f"{col} = ?")
            params.append(value)
    try:
        # Aynı kapsamdaki diğer aktif politikalar kapatılır, hedef aktifleştirilir.
        cur.execute(
            f"UPDATE criteria_completion_policies SET is_active = 0, updated_at = ? WHERE {' AND '.join(where)}",
            tuple([now] + params),
        )
        cur.execute(
            "UPDATE criteria_completion_policies SET is_active = 1, updated_at = ? WHERE id = ?",
            (now, int(policy_id)),
        )
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()
    return get_policy(conn, policy_id) or {}
