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

    P1 düzeltmesi: önceki sürüm yalnızca `scope_type='global' AND is_active=1`
    arıyordu. Eğer DB'de `scope='global', year=2026, semester='Güz', is_active=1`
    gibi yıl/dönem özel bir global politika varsa onu *varsayılan global*
    sanıp gereksiz INSERT atlanıyordu; daha kötüsü, `resolve_policy` bunu
    "varsayılan" olarak döndürebiliyordu. Sorguya `year IS NULL AND semester IS NULL`
    eklenerek "gerçek varsayılan global"a daraltıldı.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM criteria_completion_policies
        WHERE scope_type = 'global' AND is_active = 1
          AND faculty_id IS NULL AND department_id IS NULL
          AND year IS NULL AND semester IS NULL
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

    # P1: Üretim-tehlikeli politikalar için sesli uyarı. Kabul ediyoruz (test/demo
    # senaryolarını bozmamak için) ama log'a kritik düzeyde yazıyoruz ki
    # kullanıcı/operatör fark etsin. Burası hata değil çünkü politika sahibi
    # bilinçli olarak gevşek bir politika isteyebilir (örn. pilot/sandbox).
    if float(required_completion_ratio) < 0.50:
        logger.warning(
            "GEVSEK POLITIKA: name=%r required_completion_ratio=%.2f (<0.50) — "
            "hazirlik kapisini neredeyse devre disi birakir; uretimde tehlikelidir.",
            name, required_completion_ratio,
        )
    if not required_fields:
        logger.warning(
            "GEVSEK POLITIKA: name=%r required_fields BOS — zorunlu kriter yok, "
            "tamlik orani anlamsiz; uretimde tehlikelidir.",
            name,
        )

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


def _policy_candidates(
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int | None,
    semester: str | None,
) -> list[tuple[str, int | None, int | None, int | None, str | None]]:
    """Politika hiyerarşisini SİSTEMATİK olarak inşa eder.

    Önceki sürüm aday listesini elle yazıyordu ve şu adaylar **eksikti**:

      * `global + year + semester` → yıl+dönem özel global politika çözülmüyordu (P1)
      * `global + semester` (year=None) → "her yıl Güz" politikası çözülmüyordu
      * `department + semester` / `faculty + semester` (year=None) → aynı

    Çözüm: iki boyutlu kartezyen üretim
      kapsam katmanı  ∈ {department, faculty, global}  (talep edilen scope'a göre)
      zaman varyantı  ∈ {(year, semester), (year, None), (None, semester), (None, None)}

    İçten dışa: en spesifik kapsam + en spesifik zaman → en gevşek.
    """
    levels: list[tuple[str, int | None, int | None]] = []
    if scope_type == "department":
        levels.append(("department", faculty_id, department_id))
        levels.append(("faculty", faculty_id, None))
    elif scope_type == "faculty":
        levels.append(("faculty", faculty_id, None))
    # Global katman daima en sonda — son koruma bariyeri.
    levels.append(("global", None, None))

    time_variants: list[tuple[int | None, str | None]] = [
        (year, semester),
        (year, None),
        (None, semester),
        (None, None),
    ]
    # Aynı (scope, ids, time) tekrar üretmesin diye set ile dedupe ederiz.
    seen: set[tuple[str, int | None, int | None, int | None, str | None]] = set()
    out: list[tuple[str, int | None, int | None, int | None, str | None]] = []
    for scope, fid, did in levels:
        for y, sem in time_variants:
            key = (scope, fid, did, y, sem)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


# Hiç kayıt bulunmadığında DB'ye yazmadan döndürülen "in-memory" varsayılan politika.
# `auto_create_default=False` çağrılarında kullanılır; politika gerçekten oluşturulmaz.
_IN_MEMORY_DEFAULT_POLICY: dict[str, Any] = {
    "id": None,
    "name": "Varsayılan Kriter Tamlık Politikası (in-memory)",
    "scope_type": "global",
    "faculty_id": None,
    "department_id": None,
    "year": None,
    "semester": None,
    "required_completion_ratio": 1.0,
    "required_fields": list(DEFAULT_REQUIRED_FIELDS),
    "optional_fields": list(DEFAULT_OPTIONAL_FIELDS),
    "allow_new_course_missing_history": True,
    "new_course_grace_period_years": 2,
    "min_survey_response_count": None,
    "block_on_invalid_numeric": True,
    "block_on_critical_issues": True,
    "allow_override": True,
    "override_requires_reason": True,
    "override_requires_approval": True,
    "is_active": True,
    "notes": "DB'de politika kaydı bulunamadığı için bellekte üretildi (kalıcı değil).",
}


def resolve_policy(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    auto_create_default: bool = True,
) -> dict[str, Any]:
    """Seçili kapsama göre en uygun aktif tamlık politikasını hiyerarşik çözer.

    Kapsam İzolasyonu: `scope_type="faculty"` iken bölüm politikaları aranmaz;
    aday listesi parametredeki `scope_type` değerine göre kurulur. Böylece yanlışlıkla
    dolu gelmiş bir `department_id`, fakülte kapsamında bölüm politikasını uygulamaz.

    Args:
        auto_create_default: True (varsayılan, geriye dönük uyum) hiç eşleşme
            yoksa global varsayılan politikayı `commit=False` ile DB'ye yazar.
            False ise yalnızca bellek-içi varsayılan dict döner — DB'ye DOKUNMAZ.
            Salt-okuma tarafları (UI hızlı kontrolleri, log/audit) için False
            kullanın; "yazmıyorum" sözüne kesin uymak istiyorsanız.

    P1 düzeltmesi: aday listesi `_policy_candidates` ile sistematikleştirildi —
    global+year+semester, scope+semester(year=None) gibi eksik kombinasyonlar
    artık doğru sırayla aranıyor.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    # Okuma yolu: ilgisiz ID'ler kapsama göre NULL'a indirgenir (kanma yok), reddetme yok.
    scope_type, faculty_id, department_id = _validate_scope_and_ids(
        scope_type, faculty_id, department_id, strict=False
    )
    semester = _normalize_semester(semester)

    candidates = _policy_candidates(scope_type, faculty_id, department_id, year, semester)

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

    # Hiç eşleşme yoksa:
    if auto_create_default:
        # Geriye dönük uyum: varsayılan politikayı `commit=False` ile DB'ye yazıyoruz.
        # Çağıran katman commit etmezse kayıt kalıcı olmaz; ama olası yan etkiden
        # rahatsızsanız `auto_create_default=False` kullanın.
        return create_default_policy(conn, commit=False)
    return dict(_IN_MEMORY_DEFAULT_POLICY)


def list_completion_policies(
    conn: sqlite3.Connection,
    *,
    scope_type: str | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    """Politikaları listele. Tüm filtreler opsiyonel, additive — eski çağrı
    sözleşmesi (`list_completion_policies(conn)`) aynen çalışır."""
    ensure_criteria_completion_governance_schema(conn, commit=False)
    where: list[str] = ["1=1"]
    params: list[Any] = []
    if scope_type is not None:
        scope_norm = str(scope_type).strip().lower()
        if scope_norm not in VALID_SCOPE_TYPES:
            raise ValueError(f"Gecersiz scope_type filtresi: {scope_type!r}")
        where.append("scope_type = ?")
        params.append(scope_norm)
    if faculty_id is not None:
        where.append("faculty_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("department_id = ?")
        params.append(int(department_id))
    if year is not None:
        where.append("year = ?")
        params.append(int(year))
    if semester is not None:
        sem = _normalize_semester(semester)
        where.append("semester = ?")
        params.append(sem)
    if active_only:
        where.append("is_active = 1")
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM criteria_completion_policies WHERE {' AND '.join(where)} "
        f"ORDER BY is_active DESC, id DESC",
        tuple(params),
    )
    return [_row_to_dict(row) or {} for row in cur.fetchall()]


def activate_completion_policy(conn: sqlite3.Connection, policy_id: int, commit: bool = True) -> dict[str, Any]:
    """Bir politikayı aktif yapar ve aynı kapsamdaki diğerlerini atomik olarak kapatır.

    P1: Aktivasyon öncesi mevcut kayıt YENİDEN doğrulanır. Migration ya da elle
    DB müdahalesiyle bozuk kayıt oluşmuşsa (geçersiz scope/ID kombinasyonu,
    bilinmeyen kriter alanı, geçersiz dönem) aktivasyon reddedilir; bozuk bir
    politikayı sessizce aktif yapmak hazırlık kapısını yanlış kararla çalıştırır.
    """
    policy = get_policy(conn, policy_id)
    if not policy:
        raise ValueError(f"Aktivasyon hatası: {policy_id} ID'li kriter tamlık politikası bulunamadı.")
    # Re-validation: bozuk bir politikayi aktive etmeyelim.
    try:
        _validate_scope_and_ids(
            str(policy.get("scope_type") or "global"),
            policy.get("faculty_id"),
            policy.get("department_id"),
            strict=True,
        )
        _validate_policy_fields(
            policy.get("required_fields"),
            policy.get("optional_fields"),
        )
        # Eger semester saklanmis ise dogrula; None ise sorun yok.
        if policy.get("semester") is not None:
            _normalize_semester(policy.get("semester"))
        ratio = policy.get("required_completion_ratio")
        if ratio is not None and not (0.0 <= float(ratio) <= 1.0):
            raise ValueError(
                f"required_completion_ratio (DB'deki) gecersiz: {ratio}"
            )
    except ValueError as exc:
        raise ValueError(
            f"Aktivasyon reddedildi: {policy_id} ID'li politika dogrulamayi gecemedi: {exc}"
        ) from exc

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
