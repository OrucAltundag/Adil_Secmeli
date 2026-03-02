# app/services/db.py
"""
Thread-safe veritabani oturum yardimcisi.

Her thread kendi baglantisini acar; ana thread'den worker'a conn nesnesi
tasinmaz. Bu sayede sqlite3.ProgrammingError (SQLite objects created in a
thread can only be used in that same thread) hatasi onlenir.

Kullanim:
    with db_session(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT ...")
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional


DEFAULT_DB_PATH = "data/adil_secmeli.db"


def resolve_db_path(db_path: Optional[str]) -> str:
    """
    db_path None veya bos ise varsayilan yol doner.
    Relative path ise absolut hale getirir.
    """
    path = db_path or DEFAULT_DB_PATH
    if not os.path.isabs(path):
        base = os.getcwd()
        path = os.path.normpath(os.path.join(base, path))
    return path


@contextmanager
def db_session(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Thread-safe veritabani oturumu.

    Her cagrıda yeni bir baglanti acar; is bittiginde kapatir.
    Worker thread icinde guvenle kullanilir.

    Ornek:
        with db_session(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ders")
    """
    path = resolve_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Yeni bir baglanti dondurur. Cagiran kod close() ile kapatmakla yukumludur.
    Context manager kullanmak daha guvenlidir: db_session(db_path)
    """
    path = resolve_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
