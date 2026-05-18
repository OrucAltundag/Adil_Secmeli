# -*- coding: utf-8 -*-
# =============================================================================
# app/db/sqlite_db.py — UI Tarafli Veritabani Erisimi
# =============================================================================
# Tkinter UI katmani tarafindan kullanilan hafif DB wrapper.
# SQLAlchemy engine uzerinden calisir (PostgreSQL ve SQLite destekler).
# connect(), tables(), head(), read_df(), run_sql() metodlari sunar.
# =============================================================================
from __future__ import annotations

from typing import Any, Optional, Sequence

import pandas as pd
from sqlalchemy import inspect, text

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
        if db_path:
            self.connect(db_path)

    def connect(self, db_path: str | None = None) -> None:
        """Veritabanı engine'ini hazırlar. PostgreSQL'de db_path yoksayılır."""
        self._engine = get_engine()
        self._connected = True

    @property
    def conn(self):
        """Legacy uyumluluk: raw DBAPI connection döndürür.
        Dikkat: Çağıran kod close() yapmakla yükümlüdür.
        """
        self.ensure()
        return self._engine.raw_connection()

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
