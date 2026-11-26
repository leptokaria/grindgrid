import unittest
from datetime import date

from grindgrid import garmin

RAW = {"activityId": 111, "startTimeLocal": "2026-11-25 23:30:00", "activityType": {"typeKey": "trail_running"},
       "duration": 3700.5, "movingDuration": 3500.2, "elapsedDuration": 3800.0, "activityName": "Evening"}


class FakeClient:
    def __init__(self, pages=None, by_date=None):
        self.pages, self.by_date, self.calls = pages or [], by_date or [], []

    def get_activities(self, start=0, limit=20):
        self.calls.append(("page", start, limit))
        i = start // limit
        return self.pages[i] if i < len(self.pages) else []

    def get_activities_by_date(self, startdate, enddate=None):
        self.calls.append(("date", startdate, enddate))
        return self.by_date


class GarminTest(unittest.TestCase):
    def test_to_activity_maps_fields(self):
        self.assertEqual(garmin.to_activity(RAW), {
            "id": 111, "start_date_local": "2026-11-25T23:30:00", "sport_type": "trail_running",
            "moving_time": 3500, "elapsed_time": 3700})

    def test_to_activity_without_moving_duration(self):
        a = garmin.to_activity(dict(RAW, movingDuration=None))
        self.assertEqual((a["moving_time"], a["elapsed_time"]), (0, 3700))

    def test_full_fetch_paginates_until_empty(self):
        c = FakeClient(pages=[[RAW, dict(RAW, activityId=2)], [dict(RAW, activityId=3)]])
        got = garmin.fetch_activities(c, None, date(2026, 11, 26), page_size=2)
        self.assertEqual([a["id"] for a in got], [111, 2, 3])
        self.assertEqual(c.calls[-1], ("page", 4, 2))

    def test_window_fetch_uses_dates(self):
        c = FakeClient(by_date=[RAW])
        got = garmin.fetch_activities(c, date(2026, 10, 27), date(2026, 11, 26))
        self.assertEqual(c.calls, [("date", "2026-10-27", "2026-11-26")])
        self.assertEqual(len(got), 1)


if __name__ == "__main__":
    unittest.main()
