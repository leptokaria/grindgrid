"""Turn activities into one entry per grid day."""
from collections import defaultdict
from datetime import date, timedelta

GROUPS = ["run", "ride", "strength", "swim", "walk", "other"]

# Garmin Connect activityType.typeKey -> grid group
SPORT_GROUPS = {
    **dict.fromkeys(["running", "trail_running", "treadmill_running", "track_running", "indoor_running",
                     "street_running", "ultra_run", "virtual_run"], "run"),
    **dict.fromkeys(["cycling", "road_biking", "mountain_biking", "gravel_cycling", "indoor_cycling",
                     "virtual_ride", "cyclocross", "e_bike_fitness", "e_bike_mountain", "track_cycling"], "ride"),
    **dict.fromkeys(["strength_training", "hiit", "indoor_cardio"], "strength"),
    **dict.fromkeys(["lap_swimming", "open_water_swimming", "swimming"], "swim"),
    **dict.fromkeys(["walking", "casual_walking", "speed_walking", "hiking"], "walk"),
}


def sport_group(sport_type: str) -> str:
    return SPORT_GROUPS.get(sport_type, "other")


def duration(activity: dict) -> int:
    # manual gym entries often have moving_time 0
    return activity.get("moving_time") or activity.get("elapsed_time") or 0


def level(seconds: int, has_activity: bool) -> int:
    if not has_activity:
        return 0
    for lvl, limit in ((1, 1800), (2, 3600), (3, 5400)):
        if seconds <= limit:
            return lvl
    return 4


def build_days(activities: list[dict], today: date, weeks: int = 53) -> list[dict]:
    end = today + timedelta(days=6 - today.weekday())
    start = end - timedelta(days=7 * weeks - 1)
    seconds = defaultdict(int)
    by_group = defaultdict(lambda: defaultdict(int))
    for a in activities:
        # start_date_local is local time: its date prefix is the training day
        day = a["start_date_local"][:10]
        seconds[day] += duration(a)
        by_group[day][sport_group(a["sport_type"])] += duration(a)
    days = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        key = d.isoformat()
        groups = by_group.get(key)
        days.append({
            "date": key,
            "seconds": seconds.get(key, 0),
            "level": level(seconds.get(key, 0), bool(groups)),
            "sport_group": max(groups, key=groups.get) if groups else None,
            "future": d > today,
        })
    return days
