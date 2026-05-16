# app/services/db.py
"""
Thread-safe veritabani oturum yardimcisi.

SQLAlchemy session context manager saglar. PostgreSQL ve SQLite destekler.

Kullanim:
    with db_session() as session:
        result = session.execute(text("SELECT ..."))

Legacy (raw cursor) kullanim:
    conn = get_raw_connection()
    cur = conn.cursor()
    cur.execute("SELECT ...")
    conn.close()
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy.orm import Session

from app.db.database import get_engine, get_session


@contextmanager
def db_session(db_path: Optional[str] = None) -> Generator[Session, None, None]:
    """
    Thread-safe veritabani oturumu.

    Her cagrida yeni bir session acar; is bittiginde kapatir.

    Ornek:
        with db_session() as session:
            result = session.execute(text("SELECT * FROM ders"))
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_raw_connection(db_path: Optional[str] = None):
    """
    Raw DBAPI connection döndürür.

    PostgreSQL: psycopg2 connection + RealDictCursor
    SQLite:     sqlite3.Connection + Row factory

    Çağıran kod close() yapmakla yükümlüdür.
    """
    engine = get_engine()
    conn = engine.raw_connection()

    if engine.dialect.name == "sqlite":
        conn.row_factory = sqlite3.Row
    else:
        # psycopg2: cursor'larda dict-style erişim sağla
        try:
            import psycopg2.extras
            conn.cursor_factory = psycopg2.extras.RealDictCursor
        except ImportError:
            pass

    return conn


def get_conn(db_path: Optional[str] = None):
    """
    Legacy uyumluluk: Raw DBAPI connection döndürür.
    Çağıran kod close() yapmakla yükümlüdür.
    Context manager kullanmak daha güvenlidir: db_session()
    """
    return get_raw_connection(db_path)
