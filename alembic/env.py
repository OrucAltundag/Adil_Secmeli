from __future__ import annotations

from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.db.database import Base
from app.db import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_sqlalchemy_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    # config.json legacy uyumlulugu
    cfg_path = os.path.join(os.getcwd(), "config.json")
    if os.path.exists(cfg_path):
        try:
            import json

            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            db_path = data.get("db_path")
            if db_path:
                abs_path = os.path.abspath(db_path)
                return f"sqlite:///{abs_path}"
            db_url = data.get("db_url")
            if db_url:
                return db_url
        except Exception:
            pass
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    url = _resolve_sqlalchemy_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _resolve_sqlalchemy_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
