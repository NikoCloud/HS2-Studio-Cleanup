"""
core/index_db.py — SQLite index for scan caching and movement logging.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional


DB_PATH: Optional[Path] = None


def init_db(hs2_root: Path) -> None:
    global DB_PATH
    DB_PATH = hs2_root / "_StudioCleanup.db"
    with _conn() as con:
        _create_tables(con)


def _conn() -> sqlite3.Connection:
    if DB_PATH is None:
        raise RuntimeError("Database not initialised — call init_db() first.")
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def _create_tables(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id          INTEGER PRIMARY KEY,
            path        TEXT    UNIQUE NOT NULL,
            size        INTEGER NOT NULL,
            mtime       REAL    NOT NULL,
            partial_hash TEXT,
            full_hash   TEXT,
            file_type   TEXT,
            ignored     INTEGER DEFAULT 0,
            scanned_at  REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS zipmod_meta (
            file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
            guid    TEXT,
            name    TEXT,
            version TEXT,
            author  TEXT,
            game    TEXT
        );

        CREATE TABLE IF NOT EXISTS scene_dependencies (
            id       INTEGER PRIMARY KEY,
            file_id  INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
            mod_guid TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS movements (
            id            INTEGER PRIMARY KEY,
            original_path TEXT NOT NULL,
            new_path      TEXT,
            reason        TEXT NOT NULL,
            details       TEXT,
            related_file  TEXT,
            moved_at      REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_files_hash ON files(full_hash);
        CREATE INDEX IF NOT EXISTS idx_files_size ON files(size);
        CREATE INDEX IF NOT EXISTS idx_zipmod_guid ON zipmod_meta(guid);
        CREATE INDEX IF NOT EXISTS idx_scene_deps_guid ON scene_dependencies(mod_guid);
    """)


# ── File records ────────────────────────────────────────────────────────────

def is_unchanged(path: str, size: int, mtime: float) -> bool:
    """Return True if we have a cached record whose size+mtime matches."""
    with _conn() as con:
        row = con.execute(
            "SELECT size, mtime FROM files WHERE path=?", (path,)
        ).fetchone()
    if row is None:
        return False
    return row["size"] == size and abs(row["mtime"] - mtime) < 0.01


def upsert_file(path: str, size: int, mtime: float, file_type: str) -> int:
    with _conn() as con:
        con.execute("""
            INSERT INTO files (path, size, mtime, file_type, scanned_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                size=excluded.size,
                mtime=excluded.mtime,
                file_type=excluded.file_type,
                scanned_at=excluded.scanned_at
        """, (path, size, mtime, file_type, time.time()))
        return con.execute("SELECT id FROM files WHERE path=?", (path,)).fetchone()["id"]


def update_hashes(path: str, partial: str, full: str) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE files SET partial_hash=?, full_hash=? WHERE path=?",
            (partial, full, path)
        )


def get_partial_hash(path: str) -> Optional[str]:
    with _conn() as con:
        row = con.execute("SELECT partial_hash FROM files WHERE path=?", (path,)).fetchone()
    return row["partial_hash"] if row else None


def get_full_hash(path: str) -> Optional[str]:
    with _conn() as con:
        row = con.execute("SELECT full_hash FROM files WHERE path=?", (path,)).fetchone()
    return row["full_hash"] if row else None


def get_file_id(path: str) -> Optional[int]:
    with _conn() as con:
        row = con.execute("SELECT id FROM files WHERE path=?", (path,)).fetchone()
    return row["id"] if row else None


def set_ignored(path: str, ignored: bool) -> None:
    with _conn() as con:
        con.execute("UPDATE files SET ignored=? WHERE path=?", (1 if ignored else 0, path))


def get_ignored_paths() -> set[str]:
    with _conn() as con:
        rows = con.execute("SELECT path FROM files WHERE ignored=1").fetchall()
    return {r["path"] for r in rows}


def remove_missing_files(known_paths: set[str]) -> None:
    """Remove index entries for files that no longer exist on disk."""
    with _conn() as con:
        existing = {r["path"] for r in con.execute("SELECT path FROM files").fetchall()}
        to_remove = existing - known_paths
        if to_remove:
            con.executemany("DELETE FROM files WHERE path=?", [(p,) for p in to_remove])


# ── Zipmod metadata ──────────────────────────────────────────────────────────

def upsert_zipmod_meta(file_id: int, guid: str, name: str, version: str,
                       author: str, game: str) -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO zipmod_meta (file_id, guid, name, version, author, game)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_id) DO UPDATE SET
                guid=excluded.guid, name=excluded.name,
                version=excluded.version, author=excluded.author,
                game=excluded.game
        """, (file_id, guid, name, version, author, game))


def get_all_zipmods_with_meta():
    """Return rows joining files + zipmod_meta for all known zipmods."""
    with _conn() as con:
        return con.execute("""
            SELECT f.path, f.full_hash, f.size, f.ignored,
                   z.guid, z.name, z.version, z.author, z.game
            FROM files f
            LEFT JOIN zipmod_meta z ON z.file_id = f.id
            WHERE f.file_type = 'zipmod'
        """).fetchall()


# ── Scene dependencies ───────────────────────────────────────────────────────

def upsert_scene_dependencies(file_id: int, guids: list[str]) -> None:
    with _conn() as con:
        con.execute("DELETE FROM scene_dependencies WHERE file_id=?", (file_id,))
        con.executemany(
            "INSERT INTO scene_dependencies (file_id, mod_guid) VALUES (?, ?)",
            [(file_id, g) for g in guids]
        )


def get_scene_count_for_guid(mod_guid: str) -> int:
    with _conn() as con:
        row = con.execute(
            "SELECT COUNT(DISTINCT file_id) as cnt FROM scene_dependencies WHERE mod_guid=?",
            (mod_guid,)
        ).fetchone()
    return row["cnt"] if row else 0


# ── Movement log ─────────────────────────────────────────────────────────────

def record_movement(original_path: str, new_path: Optional[str],
                    reason: str, details: str = "", related_file: str = "") -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO movements (original_path, new_path, reason, details, related_file, moved_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (original_path, new_path, reason, details, related_file, time.time()))


def get_all_movements():
    with _conn() as con:
        return con.execute(
            "SELECT * FROM movements ORDER BY moved_at DESC"
        ).fetchall()


def delete_movement(movement_id: int) -> None:
    with _conn() as con:
        con.execute("DELETE FROM movements WHERE id=?", (movement_id,))
