from __future__ import annotations

import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
OBJECTS_DIR = DATA_DIR / "objects"
DB_PATH = DATA_DIR / "metadata.db"

app = FastAPI(title="Mini Bucket", version="1.0.0")


def init_storage() -> None:
    OBJECTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                content_type TEXT,
                size INTEGER NOT NULL,
                path TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER
            )
            """
        )
        conn.commit()


def cleanup_expired() -> int:
    now = int(time.time())
    removed = 0
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, path FROM files WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,),
        )
        rows = cur.fetchall()
        for file_id, path in rows:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            removed += 1
        conn.commit()
    return removed


def save_upload(upload: UploadFile, exp_seconds: Optional[int]) -> dict:
    if exp_seconds is not None and exp_seconds <= 0:
        raise HTTPException(status_code=400, detail="exp must be a positive integer (seconds)")

    file_id = uuid.uuid4().hex
    target_path = OBJECTS_DIR / file_id
    size = 0
    with target_path.open("wb") as out_file:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            out_file.write(chunk)
            size += len(chunk)

    created_at = int(time.time())
    expires_at = created_at + exp_seconds if exp_seconds is not None else None

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO files (id, filename, content_type, size, path, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                upload.filename,
                upload.content_type,
                size,
                str(target_path),
                created_at,
                expires_at,
            ),
        )
        conn.commit()

    return {
        "id": file_id,
        "filename": upload.filename,
        "content_type": upload.content_type,
        "size": size,
        "created_at": created_at,
        "expires_at": expires_at,
    }


@app.on_event("startup")
def on_startup() -> None:
    init_storage()


@app.get("/")
def root() -> dict:
    return {"status": "ok"}


@app.post("/files")
def upload_file(file: UploadFile = File(...), exp: Optional[int] = Form(None)) -> dict:
    cleanup_expired()
    result = save_upload(file, exp)
    return result


@app.get("/files")
def list_files() -> dict:
    cleanup_expired()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, filename, content_type, size, created_at, expires_at FROM files ORDER BY created_at DESC"
        )
        items = [
            {
                "id": row[0],
                "filename": row[1],
                "content_type": row[2],
                "size": row[3],
                "created_at": row[4],
                "expires_at": row[5],
            }
            for row in cur.fetchall()
        ]
    return {"items": items}


def get_file_row(file_id: str) -> Optional[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, filename, content_type, path, expires_at FROM files WHERE id = ?",
            (file_id,),
        )
        return cur.fetchone()


def get_files_by_name(filename: str) -> list[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            SELECT id, filename, content_type, size, created_at, expires_at, path
            FROM files
            WHERE filename = ?
            ORDER BY created_at DESC
            """,
            (filename,),
        )
        return cur.fetchall()


def get_latest_file_by_name(filename: str) -> Optional[tuple]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            SELECT id, filename, content_type, path, expires_at
            FROM files
            WHERE filename = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (filename,),
        )
        return cur.fetchone()


def delete_file_row(file_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT path FROM files WHERE id = ?", (file_id,))
        row = cur.fetchone()
        if not row:
            return False
        path = row[0]
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        return True


def delete_files_by_name(filename: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT id, path FROM files WHERE filename = ?", (filename,))
        rows = cur.fetchall()
        if not rows:
            return 0
        for _file_id, path in rows:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
        conn.execute("DELETE FROM files WHERE filename = ?", (filename,))
        conn.commit()
        return len(rows)


@app.get("/files/{file_id}")
def download_file(file_id: str) -> FileResponse:
    cleanup_expired()
    row = get_file_row(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="file not found")
    _, filename, content_type, path, _expires_at = row
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=file_path, filename=filename, media_type=content_type)


@app.get("/files/by-name/{filename}")
def list_files_by_name(filename: str) -> dict:
    cleanup_expired()
    rows = get_files_by_name(filename)
    if not rows:
        raise HTTPException(status_code=404, detail="file not found")
    items = [
        {
            "id": row[0],
            "filename": row[1],
            "content_type": row[2],
            "size": row[3],
            "created_at": row[4],
            "expires_at": row[5],
        }
        for row in rows
    ]
    return {"items": items}


@app.get("/files/by-name/{filename}/download")
def download_file_by_name(filename: str) -> FileResponse:
    cleanup_expired()
    row = get_latest_file_by_name(filename)
    if not row:
        raise HTTPException(status_code=404, detail="file not found")
    _, found_name, content_type, path, _expires_at = row
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=file_path, filename=found_name, media_type=content_type)


@app.delete("/files/{file_id}")
def delete_file(file_id: str) -> dict:
    cleanup_expired()
    deleted = delete_file_row(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="file not found")
    return {"deleted": True}


@app.delete("/files/by-name/{filename}")
def delete_file_by_name(filename: str) -> dict:
    cleanup_expired()
    deleted_count = delete_files_by_name(filename)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="file not found")
    return {"deleted": True, "count": deleted_count}
