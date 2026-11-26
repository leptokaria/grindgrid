"""Pull activities from Strava into SQLite. Run hourly by a systemd timer."""
import argparse
import calendar
import os
import random
import sys
from datetime import date, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from grindgrid import db, strava

RESYNC_DAYS = 30


def sync(conn, fetch: Callable[[int | None], list[dict]], today: date, full: bool = False) -> tuple[int, int]:
    latest = db.latest_start(conn)
    if full or latest is None:
        after, since = None, ""
    else:
        start = min(date.fromisoformat(latest[:10]), today - timedelta(days=RESYNC_DAYS))
        # Strava filters `after` on UTC start; fetch one extra day so local-date deletes never outrun it
        after, since = calendar.timegm(start.timetuple()) - 86400, start.isoformat()
    activities = fetch(after)  # raises before anything is deleted
    db.upsert(conn, activities)
    return len(activities), db.delete_missing(conn, since, {a["id"] for a in activities})


def demo_activities(today: date, seed: int = 1) -> list[dict]:
    rng = random.Random(seed)
    sports = ["Run", "Run", "Ride", "WeightTraining", "Swim", "Walk", "Yoga"]
    out, next_id = [], 10**9
    for i in range(365):
        day = today - timedelta(days=i)
        for _ in range(rng.choices([0, 1, 2], [45, 45, 10])[0]):
            out.append({"id": next_id, "start_date_local": f"{day}T{rng.randint(6, 20):02d}:00:00Z",
                        "sport_type": rng.choice(sports), "moving_time": rng.randint(15, 120) * 60,
                        "elapsed_time": 0})
            next_id += 1
    return out


def today_in(tz: str) -> date:
    return datetime.now(ZoneInfo(tz)).date()


def data_dir() -> str:
    data = os.environ.get("GRINDGRID_DATA", "/var/lib/grindgrid")
    os.makedirs(data, exist_ok=True)
    return data


def db_path() -> str:
    return os.path.join(data_dir(), "grindgrid.db")


def token_path() -> str:
    return os.path.join(data_dir(), "tokens.json")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="grindgrid.sync")
    p.add_argument("--full", action="store_true", help="refetch whole history")
    p.add_argument("--demo", action="store_true", help="replace DB with fake data (no network)")
    args = p.parse_args(argv)
    today = today_in(os.environ.get("TZ", "Europe/Warsaw"))
    conn = db.connect(db_path())
    if args.demo:
        with conn:
            conn.execute("DELETE FROM activities")
        db.upsert(conn, demo_activities(today))
        print("demo data loaded")
        return 0
    tokens = token_path()
    if not os.path.exists(tokens):
        print("no Strava tokens: open /auth first", file=sys.stderr)
        return 1
    cid, secret = os.environ["STRAVA_CLIENT_ID"], os.environ["STRAVA_CLIENT_SECRET"]
    fetch = lambda after: strava.fetch_activities(strava.access_token(cid, secret, tokens), after)
    added, deleted = sync(conn, fetch, today, full=args.full)
    print(f"synced {added} activities, removed {deleted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
