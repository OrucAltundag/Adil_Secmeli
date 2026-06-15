# -*- coding: utf-8 -*-
"""Import geçmişi temizleme servisi.

Import geçmişindeki kargaşayı azaltmak için terminal (tamamlanmış, artık aktif
olmayan) import batch kayıtlarını **arşiv tablosuna taşır**; canlı/işlemde veya
karara bağlı kayıtları korur. Gerçek veri tabloları (ders/havuz/mufredat/skor
vb.) ASLA silinmez — yalnız import geçmişi/işlem logları temizlenir.

UI bu servisi çağırır; servis kullanıcıya dönük güvenli orkestrasyon + özet
mesaj üretir. SQL erişimi repository katmanındadır.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.import_repository import (
    archive_import_history,
    count_protected_import_batches,
    get_cleanable_import_batches,
    get_import_history,
)


def _batch_ids(rows: list[dict[str, Any]]) -> list[int]:
    return [int(rid) for r in rows if (rid := r.get("id")) is not None]


def preview_cleanup(conn: sqlite3.Connection) -> dict[str, Any]:
    """Temizleme öncesi özet: kaç kayıt temizlenebilir, kaçı korunacak."""
    cleanable = get_cleanable_import_batches(conn)
    protected = count_protected_import_batches(conn)
    return {
        "cleanable_count": len(cleanable),
        "protected_count": int(protected),
        "cleanable_ids": _batch_ids(cleanable),
    }


def cleanup_import_history(
    conn: sqlite3.Connection,
    user: str | None = None,
    reason: str | None = "UI üzerinden import geçmişi temizleme.",
) -> dict[str, Any]:
    """Temizlenebilir batch'leri arşivler. Caller commit etmeli.

    Dönüş: {ok, archived, protected, logs_removed, message}
    """
    cleanable = get_cleanable_import_batches(conn)
    protected = count_protected_import_batches(conn)
    if not cleanable:
        return {
            "ok": True,
            "archived": 0,
            "protected": int(protected),
            "logs_removed": 0,
            "message": f"Temizlenecek eski import kaydı yok. {protected} aktif/korunan kayıt mevcut.",
        }
    batch_ids = _batch_ids(cleanable)
    outcome = archive_import_history(conn, batch_ids, archived_by=user, reason=reason)
    archived = int(outcome.get("archived", 0))
    return {
        "ok": True,
        "archived": archived,
        "protected": int(protected),
        "logs_removed": int(outcome.get("logs_removed", 0)),
        "message": (
            f"Import geçmişi temizlendi. {archived} eski kayıt arşivlendi, "
            f"{protected} aktif/korunan kayıt korundu."
        ),
    }


def list_history(conn: sqlite3.Connection, limit: int = 500) -> list[dict[str, Any]]:
    """Aktif import geçmişi listesi (UI yenileme için)."""
    return get_import_history(conn, limit=limit)
