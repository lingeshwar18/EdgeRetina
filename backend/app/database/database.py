import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(path: Path) -> None:
    with connect(path) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_filename TEXT NOT NULL,
            predicted_class INTEGER NOT NULL,
            severity_label TEXT NOT NULL,
            confidence REAL NOT NULL,
            model_source TEXT NOT NULL,
            gradcam_path TEXT,
            created_at TEXT NOT NULL
        )""")


def add_prediction(path: Path, filename: str, class_id: int, label: str, confidence: float, model_source: str, gradcam_path: str | None = None) -> int:
    with connect(path) as connection:
        cursor = connection.execute(
            "INSERT INTO predictions (image_filename, predicted_class, severity_label, confidence, model_source, gradcam_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (filename, class_id, label, confidence, model_source, gradcam_path, datetime.now(timezone.utc).isoformat()),
        )
        return int(cursor.lastrowid)


def list_predictions(path: Path, query: str = "", class_id: int | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM predictions WHERE image_filename LIKE ?"
    params: list[object] = [f"%{query}%"]
    if class_id is not None:
        sql += " AND predicted_class = ?"
        params.append(class_id)
    sql += " ORDER BY created_at DESC"
    with connect(path) as connection:
        return connection.execute(sql, params).fetchall()
