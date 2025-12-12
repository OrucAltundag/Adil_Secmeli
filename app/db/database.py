# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import json, os

def _load_db_url():
    # config.json varsa oradan oku; yoksa varsayılan sqlite dosyası
    cfg = {"db_url": "sqlite:///./adil_secimli.db"}
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if "db_path" in data:
                cfg["db_url"] = f"sqlite:///{os.path.abspath(data['db_path'])}"
            elif "db_url" in data:
                cfg["db_url"] = data["db_url"]
        except Exception:
            pass
    return cfg["db_url"]

DATABASE_URL = _load_db_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()
