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

from contextlib import contextmanager
from typing import Generator, Optional

from app.db.session import db_session as legacy_db_session
from app.db.session import open_sqlite_connection


@contextmanager
def db_session(db_path: Optional[str] = None) -> Generator[object, None, None]:
    """
    Thread-safe legacy SQLite oturumu.

    Her cagrida yeni bir sqlite3 connection acar; is bittiginde kapatir.

    Ornek:
        with db_session() as conn:
            cur = conn.cursor()
    """
    with legacy_db_session(db_path) as conn:
        yield conn


def get_raw_connection(db_path: Optional[str] = None):
    """
    Raw DBAPI connection döndürür.

    PostgreSQL: psycopg2 connection + RealDictCursor
    SQLite:     sqlite3.Connection + Row factory

    Çağıran kod close() yapmakla yükümlüdür.
    """
    return open_sqlite_connection(db_path, row_factory=True)


def get_conn(db_path: Optional[str] = None):
    """
    Legacy uyumluluk: Raw DBAPI connection döndürür.
    Çağıran kod close() yapmakla yükümlüdür.
    Context manager kullanmak daha güvenlidir: db_session()
    """
    return get_raw_connection(db_path)
