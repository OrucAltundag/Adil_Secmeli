# -*- coding: utf-8 -*-
"""Import governance kayıtları için repository.

Sınıf tabanlı `ImportRepository` basit listeleme için kalır. Import geçmişi
temizleme (arşivleme) için modül seviyesinde fonksiyonlar eklenmiştir.

Temizleme felsefesi (kullanıcı kararı): **arşiv tablosuna taşıma**.
- Temizlenebilir = terminal durum (superseded/rejected/rolled_back/failed) **ve**
  bir karar çalıştırmasına kaynaklık etmeyen (`decision_run_import_sources`).
- Korunan = işlemdeki/canlı durumlar (uploaded/validated/pending_review/approved/active)
  ve karara bağlı her batch.
- Arşivleme: batch satırı `import_batches_archive` tablosuna kopyalanır, ilişkili
  log/staging çocuk kayıtları temizlenir, batch ana tablodan silinir.
- Gerçek veri tabloları (ders, havuz, mufredat, skor, ders_kriterleri, anket vb.)
  ASLA dokunulmaz.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.repositories.base import fetch_all_dicts

CLEANABLE_STATUSES = ("superseded", "rejected", "rolled_back", "failed")
PROTECTED_STATUSES = ("uploaded", "validated", "pending_review", "approved", "active")

# import_batch_id kolonu olan ve temizlenmesi güvenli log/staging tabloları.
# decision_run_import_sources KASITEN dışarıda: karar bağı koruma sebebidir.
_CHILD_TABLES_BY_BATCH = (
    "survey_import_rows",
    "survey_import",
    "criteria_import_rows",
    "criteria_import",
    "import_quality_checks",
    "import_row_issues",
    "import_rollback_logs",
    "import_impact_reports",
)


class ImportRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_batches(self, limit: int = 200) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM import_batches ORDER BY id DESC LIMIT ?", (int(limit),))
        return fetch_all_dicts(cur)


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
    return bool(cur.fetchone())


def _columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [str(r[1]) for r in cur.fetchall()]


def ensure_import_archive_schema(conn: sqlite3.Connection, commit: bool = False) -> None:
    """import_batches_archive tablosunu (yoksa) oluşturur.

    import_batches ile aynı kolonlar + arşiv meta (archived_at/by/reason).
    Şema additive; mevcut import akışını etkilemez.
    """
    cur = conn.cursor()
    if not _table_exists(cur, "import_batches"):
        return
    if _table_exists(cur, "import_batches_archive"):
        return
    base_cols = _columns(cur, "import_batches")
    # id dahil tüm kolonları metin/again esnek tutmak için TEXT'e yakın; ancak
    # basitlik ve uyum için orijinal tipleri kopyalamak yerine genel tablo kurarız.
    col_defs = ", ".join(f'"{c}"' for c in base_cols)
    cur.execute(
        f"""
        CREATE TABLE import_batches_archive AS
        SELECT {col_defs} FROM import_batches WHERE 0
        """
    )
    cur.execute('ALTER TABLE import_batches_archive ADD COLUMN archived_at TEXT')
    cur.execute('ALTER TABLE import_batches_archive ADD COLUMN archived_by TEXT')
    cur.execute('ALTER TABLE import_batches_archive ADD COLUMN archive_reason TEXT')
    if commit:
        conn.commit()


def _protected_by_decision_ids(cur: sqlite3.Cursor) -> set[int]:
    if not _table_exists(cur, "decision_run_import_sources"):
        return set()
    cur.execute("SELECT DISTINCT import_batch_id FROM decision_run_import_sources WHERE import_batch_id IS NOT NULL")
    return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}


# ---------------------------------------------------------------------------
# Okuma fonksiyonları (spec'teki repository imzaları)
# ---------------------------------------------------------------------------


def get_import_history(conn: sqlite3.Connection, limit: int = 500) -> list[dict[str, Any]]:
    """Aktif import geçmişi (arşivlenmemiş, çünkü arşivlenenler taşınır)."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM import_batches ORDER BY id DESC LIMIT ?", (int(limit),))
    return fetch_all_dicts(cur)


def refresh_import_history_view(conn: sqlite3.Connection, limit: int = 500) -> list[dict[str, Any]]:
    """get_import_history için anlamca eşdeğer (UI yeniden okuma çağrısı)."""
    return get_import_history(conn, limit=limit)


def get_cleanable_import_batches(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Temizlenebilir (terminal + karara bağlı olmayan) batch'ler."""
    cur = conn.cursor()
    if not _table_exists(cur, "import_batches"):
        return []
    protected = _protected_by_decision_ids(cur)
    placeholders = ",".join("?" for _ in CLEANABLE_STATUSES)
    cur.execute(
        f"SELECT * FROM import_batches WHERE status IN ({placeholders}) ORDER BY id DESC",
        CLEANABLE_STATUSES,
    )
    rows = fetch_all_dicts(cur)
    return [r for r in rows if (rid := r.get("id")) is not None and int(rid) not in protected]


def count_protected_import_batches(conn: sqlite3.Connection) -> int:
    """Korunan batch sayısı (canlı/işlemde durumlar + karara bağlı olanlar)."""
    cur = conn.cursor()
    if not _table_exists(cur, "import_batches"):
        return 0
    cur.execute("SELECT id, status FROM import_batches")
    rows = cur.fetchall()
    protected = _protected_by_decision_ids(cur)
    count = 0
    for bid, status in rows:
        if status in PROTECTED_STATUSES or (bid is not None and int(bid) in protected):
            count += 1
    return count


def _purge_children(cur: sqlite3.Cursor, batch_ids: list[int]) -> int:
    """Verilen batch'lere ait log/staging çocuk kayıtlarını siler. Silinen toplam satır."""
    if not batch_ids:
        return 0
    placeholders = ",".join("?" for _ in batch_ids)
    params = tuple(int(b) for b in batch_ids)
    removed = 0
    # import_diff_items, import_diffs.id üzerinden (FK kolon adı şemaya göre değişebilir)
    if _table_exists(cur, "import_diffs") and _table_exists(cur, "import_diff_items"):
        item_cols = _columns(cur, "import_diff_items")
        fk_col = next((c for c in ("import_diff_id", "diff_id") if c in item_cols), None)
        if fk_col:
            cur.execute(
                f"DELETE FROM import_diff_items WHERE {fk_col} IN "
                f"(SELECT id FROM import_diffs WHERE import_batch_id IN ({placeholders}))",
                params,
            )
            removed += cur.rowcount or 0
    for table in ("import_diffs",) + _CHILD_TABLES_BY_BATCH:
        if not _table_exists(cur, table):
            continue
        if "import_batch_id" not in _columns(cur, table):
            continue
        cur.execute(f"DELETE FROM {table} WHERE import_batch_id IN ({placeholders})", params)
        removed += cur.rowcount or 0
    return removed


def archive_import_history(
    conn: sqlite3.Connection,
    batch_ids: list[int],
    archived_by: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Verilen batch'leri arşiv tablosuna taşır, log/staging çocuklarını temizler.

    Caller commit eder. Gerçek veri tablolarına dokunmaz.
    """
    ids = [int(b) for b in dict.fromkeys(batch_ids)]
    if not ids:
        return {"archived": 0, "logs_removed": 0}
    ensure_import_archive_schema(conn, commit=False)
    cur = conn.cursor()
    base_cols = _columns(cur, "import_batches")
    placeholders = ",".join("?" for _ in ids)
    col_list = ", ".join(f'"{c}"' for c in base_cols)
    now = _now()
    # Arşive kopyala
    cur.execute(
        f"""
        INSERT INTO import_batches_archive ({col_list}, archived_at, archived_by, archive_reason)
        SELECT {col_list}, ?, ?, ? FROM import_batches WHERE id IN ({placeholders})
        """,
        (now, archived_by, reason, *ids),
    )
    archived = cur.rowcount or 0
    logs_removed = _purge_children(cur, ids)
    cur.execute(f"DELETE FROM import_batches WHERE id IN ({placeholders})", tuple(ids))
    return {"archived": archived, "logs_removed": logs_removed, "batch_ids": ids}


def delete_import_history(conn: sqlite3.Connection, batch_ids: list[int]) -> dict[str, Any]:
    """Arşivlemeden kalıcı siler (log/staging dahil). Caller commit eder.

    Varsayılan akışta kullanılmaz; arşivleme tercih edilir.
    """
    ids = [int(b) for b in dict.fromkeys(batch_ids)]
    if not ids:
        return {"deleted": 0, "logs_removed": 0}
    cur = conn.cursor()
    logs_removed = _purge_children(cur, ids)
    placeholders = ",".join("?" for _ in ids)
    cur.execute(f"DELETE FROM import_batches WHERE id IN ({placeholders})", tuple(ids))
    return {"deleted": cur.rowcount or 0, "logs_removed": logs_removed, "batch_ids": ids}
