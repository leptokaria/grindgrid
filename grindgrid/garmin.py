"""Garmin Connect source, via the unofficial python-garminconnect library.

One-time login on the server:  python -m grindgrid.garmin
"""
import getpass
import os
import sys
from datetime import date


def to_activity(raw: dict) -> dict:
    return {
        "id": raw["activityId"],
        # startTimeLocal is "YYYY-MM-DD HH:MM:SS" in the activity's own local time
        "start_date_local": raw["startTimeLocal"].replace(" ", "T"),
        "sport_type": raw["activityType"]["typeKey"],
        "moving_time": int(raw.get("movingDuration") or 0),
        "elapsed_time": int(raw.get("duration") or raw.get("elapsedDuration") or 0),
    }


def fetch_activities(client, since: date | None, today: date, page_size: int = 100) -> list[dict]:
    if since is not None:
        return [to_activity(a) for a in client.get_activities_by_date(since.isoformat(), today.isoformat())]
    out, start = [], 0
    while batch := client.get_activities(start, page_size):
        out += [to_activity(a) for a in batch]
        start += page_size
    return out


def client(token_dir: str):
    from garminconnect import Garmin  # imported lazily so tests and --demo need no dependency
    g = Garmin()
    g.login(token_dir)
    return g


def login_main(token_dir: str) -> int:
    from garminconnect import Garmin
    email = input("Garmin e-mail: ")
    password = getpass.getpass("Garmin password (not stored): ")
    os.makedirs(token_dir, mode=0o700, exist_ok=True)
    Garmin(email, password, prompt_mfa=lambda: input("MFA code: ")).login(token_dir)
    print(f"Logged in, tokens saved in {token_dir}")
    return 0


if __name__ == "__main__":
    from grindgrid.sync import garmin_token_dir
    sys.exit(login_main(garmin_token_dir()))
