import unittest
from datetime import date

from grindgrid.days import build_days, duration, level, sport_group


def act(day, sport="Run", moving=1800, elapsed=None, id=1):
    return {"id": id, "start_date_local": f"{day}T07:00:00Z", "sport_type": sport,
            "moving_time": moving, "elapsed_time": elapsed if elapsed is not None else moving}


class DaysTest(unittest.TestCase):
    def test_level_thresholds(self):
        self.assertEqual(level(0, False), 0)
        self.assertEqual(level(0, True), 1)
        self.assertEqual(level(1800, True), 1)
        self.assertEqual(level(1801, True), 2)
        self.assertEqual(level(3600, True), 2)
        self.assertEqual(level(5400, True), 3)
        self.assertEqual(level(5401, True), 4)

    def test_duration_falls_back_to_elapsed(self):
        self.assertEqual(duration({"moving_time": 0, "elapsed_time": 3000}), 3000)
        self.assertEqual(duration({"moving_time": 1200, "elapsed_time": 3000}), 1200)

    def test_unknown_sport_is_other(self):
        self.assertEqual(sport_group("Pickleball"), "other")
        self.assertEqual(sport_group("Yoga"), "other")
        self.assertEqual(sport_group("TrailRun"), "run")

    def test_day_uses_local_date_prefix(self):
        a = act("2026-11-25")
        a["start_date_local"] = "2026-11-25T23:30:00Z"
        days = {d["date"]: d for d in build_days([a], date(2026, 11, 26))}
        self.assertEqual(days["2026-11-25"]["seconds"], 1800)
        self.assertEqual(days["2026-11-26"]["seconds"], 0)

    def test_same_day_sums_and_dominant_sport(self):
        acts = [act("2026-11-24", "Run", 1200, id=1), act("2026-11-24", "WeightTraining", 2400, id=2)]
        d = {d["date"]: d for d in build_days(acts, date(2026, 11, 26))}["2026-11-24"]
        self.assertEqual(d["seconds"], 3600)
        self.assertEqual(d["level"], 2)
        self.assertEqual(d["sport_group"], "strength")

    def test_window_shape(self):
        days = build_days([], date(2026, 11, 26), weeks=53)
        self.assertEqual(len(days), 371)
        self.assertEqual(date.fromisoformat(days[0]["date"]).weekday(), 0)
        self.assertEqual(days[-1]["date"], "2026-11-29")
        self.assertEqual([d["future"] for d in days[-4:]], [False, True, True, True])
        self.assertTrue(all(d["level"] == 0 and d["sport_group"] is None for d in days))


if __name__ == "__main__":
    unittest.main()
