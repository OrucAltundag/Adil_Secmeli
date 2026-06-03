import json
import os

from app.core.config import load_app_config, resolve_sqlite_db_path
from app.db.sqlite_db import Database


def test_missing_config_db_path_falls_back_to_project_default(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"db_path": str(tmp_path / "missing.db"), "db_url": f"sqlite:///{tmp_path / 'missing.db'}"}),
        encoding="utf-8",
    )

    config = load_app_config(str(config_path))

    assert config.sqlite_db_path == str(resolve_sqlite_db_path())
    assert config.database_url == f"sqlite:///{resolve_sqlite_db_path().as_posix()}"


def test_database_runtime_target_updates_sqlite_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    db_path = tmp_path / "chosen.db"

    Database._apply_runtime_target(str(db_path))

    assert os.environ["SQLITE_DB_PATH"] == str(db_path.resolve())
    assert os.environ["DATABASE_URL"] == f"sqlite:///{db_path.resolve().as_posix()}"
