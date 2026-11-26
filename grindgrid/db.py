"""SQLite store for activities (only the fields the grid needs)."""
import sqlite3

FIELDS = ("id", "start_date_local", "sport_type", "moving_time", "elapsed_time")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS activities (id INTEGER PRIMARY KEY, start_date_local TEXT,"
                 " sport_type TEXT, moving_time INTEGER, elapsed_time INTEGER)")
    return conn


def upsert(conn, activities: list[dict]) -> None:
    with conn:
        conn.executemany("INSERT OR REPLACE INTO activities VALUES (?, ?, ?, ?, ?)",
                         [tuple(a.get(f) for f in FIELDS) for a in activities])


def delete_missing(conn, since_date: str, keep_ids: set[int]) -> int:
    rows = conn.execute("SELECT id FROM activities WHERE start_date_local >= ?", (since_date,))
    gone = [r["id"] for r in rows if r["id"] not in keep_ids]
    with conn:
        conn.executemany("DELETE FROM activities WHERE id = ?", [(i,) for i in gone])
    return len(gone)


def all_activities(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM activities ORDER BY start_date_local")]


def latest_start(conn) -> str | None:
    return conn.execute("SELECT MAX(start_date_local) FROM activities").fetchone()[0]
