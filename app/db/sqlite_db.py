# -*- coding: utf-8 -*-
# =============================================================================
# app/db/sqlite_db.py — UI Tarafli Veritabani Erisimi
# =============================================================================
# Tkinter UI katmani tarafindan kullanilan hafif DB wrapper.
# SQLAlchemy engine uzerinden calisir (PostgreSQL ve SQLite destekler).
# connect(), tables(), head(), read_df(), run_sql() metodlari sunar.
# =============================================================================
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine.url import make_url

from app.db.database import get_engine


class Database:
    """
    UI tarafı için SQLAlchemy tabanlı küçük DB wrapper.
    - connect()      (artık sadece engine'i hazırlar)
    - tables()
    - head()
    - read_df()
    - run_sql()

    Not: run_sql SELECT ise (cols, rows) döner, değilse commit yapar.
    """

    def __init__(self, db_path: Optional[str] = None):
        self._engine = None
        self._connected = False
        # Uzun omurlu (long-lived) tek UI baglantisi. `.conn` her erisimde
        # havuzdan YENI baglanti cekerse (eski davranis) QueuePool (size 5 +
        # overflow 10) ~15 erisimde tukenir ve sonraki erisim 30sn bloklanir
        # -> "Yanit Vermiyor". Tek baglantiyi cache'leyerek bunu onluyoruz.
        self._raw_conn = None
        if db_path:
            self.connect(db_path)

    @staticmethod
    def _apply_runtime_target(db_path: str | None) -> None:
        if not db_path:
            return
        raw = str(db_path).strip()
        if not raw:
            return

        if "://" in raw:
            os.environ["DATABASE_URL"] = raw
            try:
                parsed = make_url(raw)
                if parsed.get_backend_name() == "sqlite" and parsed.database and parsed.database != ":memory:":
                    sqlite_path = Path(parsed.database)
                    if not sqlite_path.is_absolute():
                        sqlite_path = sqlite_path.resolve()
                    os.environ["SQLITE_DB_PATH"] = str(sqlite_path)
            except Exception:
                pass
            return

        sqlite_path = Path(raw).expanduser().resolve()
        os.environ["SQLITE_DB_PATH"] = str(sqlite_path)
        os.environ["DATABASE_URL"] = f"sqlite:///{sqlite_path.as_posix()}"

    def connect(self, db_path: str | None = None) -> None:
        """Veritabanı engine'ini hazırlar."""
        self._apply_runtime_target(db_path)
        # Hedef (re)baglanti degisti -> eski cache'lenmis baglantiyi birak.
        self._discard_cached_conn()
        self._engine = get_engine()
        self._connected = True

    def _discard_cached_conn(self) -> None:
        """Cache'lenmis UI baglantisini havuza geri ver / kapat."""
        existing = self._raw_conn
        self._raw_conn = None
        if existing is not None:
            try:
                existing.close()
            except Exception:
                pass

    @property
    def conn(self):
        """Legacy uyumluluk: uzun omurlu (long-lived) tek DBAPI baglantisi.

        Eski Tkinter kodu `.conn`'u tek bir kalici sqlite3 baglantisi gibi
        kullaniyor: tekrar tekrar erisir, ayni baglanti uzerinde commit()
        yapar ve genelde close() etmez. SQLAlchemy gecisinde `.conn` her
        erisimde havuzdan YENI bir `raw_connection()` donduruyordu; bu hem
        commit()'i farkli baglantiya yaziyor hem de havuzu (size 5 +
        overflow 10) ~15 erisimde tuketip 30sn'lik kilitlenmeye
        ("Yanit Vermiyor") yol aciyordu. Cozum: tek baglantiyi cache'le.

        Ayrica `conn.row_factory = sqlite3.Row` proxy'ye (_ConnectionFairy)
        yazildiginda alttaki DBAPI baglantisina ulasmaz; bu yuzden
        row_factory'yi driver baglantisina da yaziyoruz (aksi halde
        `data.get("id")` None donup profil id=0 oluyor ve satirlar eleniyor).
        """
        self.ensure()
        existing = self._raw_conn
        if existing is not None:
            try:
                # Ucuz canlilik kontrolu: kapali/bozuksa hata firlatir.
                existing.cursor().close()
                return existing
            except Exception:
                self._discard_cached_conn()
        proxy = self._engine.raw_connection()
        driver_conn = getattr(proxy, "driver_connection", None) or getattr(
            proxy, "connection", None
        )
        if isinstance(driver_conn, sqlite3.Connection):
            driver_conn.row_factory = sqlite3.Row
        self._raw_conn = proxy
        return proxy

    @conn.setter
    def conn(self, value):
        """`self.db.conn = None` ile baglantiyi serbest birakma destegi
        (tools_tab harici servis islemlerinden once cagiriyor)."""
        if value is None:
            self._discard_cached_conn()
        else:
            self._raw_conn = value

    def ensure(self) -> None:
        if not self._connected or self._engine is None:
            # Otomatik bağlan
            try:
                self.connect()
            except Exception as e:
                raise RuntimeError(f"Veritabanı bağlantısı kurulamadı: {str(e)}")
        if self._engine is None:
            raise RuntimeError(
                "Veritabanı motoru başlatılamadı. Config.json'daki db_path ve db_url değerlerini kontrol edin."
            )

    def tables(self) -> list[str]:
        self.ensure()
        insp = inspect(self._engine)
        all_tables = insp.get_table_names()
        return sorted([t for t in all_tables if not t.startswith("sqlite_")])

    def get_columns(self, table: str) -> set[str]:
        """Tablonun kolon isimlerini döndürür."""
        self.ensure()
        insp = inspect(self._engine)
        if not insp.has_table(table):
            return set()
        return {col["name"] for col in insp.get_columns(table)}

    def head(self, table: str, limit: int = 1000) -> tuple[list[str], list[Any]]:
        self.ensure()
        with self._engine.connect() as conn:
            result = conn.execute(text(f'SELECT * FROM "{table}" LIMIT :lim'), {"lim": int(limit)})
            cols = list(result.keys())
            rows = [tuple(row) for row in result.fetchall()]
        return cols, rows

    def read_df(self, query: str, params=None):
        self.ensure()
        with self._engine.connect() as conn:
            if params is None:
                return pd.read_sql_query(text(query), conn)
            return pd.read_sql_query(text(query), conn, params=params)

    def run_sql(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> tuple[list[str], list[Any]]:
        """
        SELECT => (cols, rows)
        Diğer => commit ve ([], [])
        """
        self.ensure()
        # Parametreleri ? yerine :param formatına dönüştür
        processed_query, processed_params = self._adapt_params(query, params)

        with self._engine.connect() as conn:
            if processed_params:
                result = conn.execute(text(processed_query), processed_params)
            else:
                result = conn.execute(text(processed_query))

            if query.strip().lower().startswith("select"):
                cols = list(result.keys())
                rows = [tuple(row) for row in result.fetchall()]
                return cols, rows

            conn.commit()
            return [], []

    @staticmethod
    def _adapt_params(
        query: str, params: Optional[Sequence[Any]]
    ) -> tuple[str, dict[str, Any] | None]:
        """SQLite ? parametrelerini SQLAlchemy :param formatına dönüştürür."""
        if params is None:
            return query, None

        # ? placeholder'ları :p0, :p1, :p2 ... ile değiştir
        param_dict = {}
        counter = [0]

        def replacer(match):
            idx = counter[0]
            counter[0] += 1
            key = f"p{idx}"
            if idx < len(params):
                param_dict[key] = params[idx]
            return f":{key}"

        import re

        # Sadece string dışındaki ? işaretlerini değiştir
        new_query = re.sub(r"\?", replacer, query)
        return new_query, param_dict if param_dict else None
