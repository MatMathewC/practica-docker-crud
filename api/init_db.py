"""Inicializacion idempotente de SQLite para la practica."""
import os
import sqlite3
from pathlib import Path


def db_path():
    return Path(os.environ.get("DB_PATH", "/data/app.db"))


def init_db():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=5) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL CHECK (precio >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
    return path


if __name__ == "__main__":
    print(f"Base de datos inicializada: {init_db()}")
