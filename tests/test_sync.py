import unittest
from datetime import date

from grindgrid import db
from grindgrid.sync import demo_activities, sync


def act(id, day, sport="Run"):
    return {"id": id, "start_date_local": f"{day}T07:00:00Z", "sport_type": sport,
            "moving_time": 1800, "elapsed_time": 1900}


class FakeFetch:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result or [], error, []

    def __call__(self, after):
        self.calls.append(after)
        if self.error:
            raise self.error
        return self.result


TODAY = date(2026, 11, 26)


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")

    def test_first_sync_fetches_full_history(self):
        fetch = FakeFetch([act(1, "2025-01-01"), act(2, "2026-11-20")])
        self.assertEqual(sync(self.conn, fetch, TODAY), (2, 0))
        self.assertEqual(fetch.calls, [None])
        self.assertEqual({a["id"] for a in db.all_activities(self.conn)}, {1, 2})

    def test_incremental_refetches_last_30_days(self):
        db.upsert(self.conn, [act(1, "2026-11-20")])
        fetch = FakeFetch([act(1, "2026-11-20")])
        sync(self.conn, fetch, TODAY)
        self.assertEqual(fetch.calls, [date(2026, 10, 27)])

    def test_deleted_at_source_removed_in_window(self):
        db.upsert(self.conn, [act(1, "2026-01-05"), act(2, "2026-11-20"), act(3, "2026-11-21")])
        fetch = FakeFetch([act(3, "2026-11-21")])
        self.assertEqual(sync(self.conn, fetch, TODAY), (1, 1))
        self.assertEqual({a["id"] for a in db.all_activities(self.conn)}, {1, 3})

    def test_fetch_failure_deletes_nothing(self):
        db.upsert(self.conn, [act(1, "2026-11-20"), act(2, "2026-11-21")])
        with self.assertRaises(RuntimeError):
            sync(self.conn, FakeFetch(error=RuntimeError("429")), TODAY)
        self.assertEqual(len(db.all_activities(self.conn)), 2)

    def test_full_resync_deletes_anything_missing(self):
        db.upsert(self.conn, [act(1, "2025-01-05"), act(2, "2026-11-20")])
        fetch = FakeFetch([act(2, "2026-11-20")])
        self.assertEqual(sync(self.conn, fetch, TODAY, full=True), (1, 1))
        self.assertEqual(fetch.calls, [None])

    def test_edge_day_after_local_midnight_not_deleted(self):
        # run at local 00:30 on the window's first day; fetch filters by local date like Garmin
        edge = act(7, "2026-10-27")
        edge["start_date_local"] = "2026-10-27T00:30:00"
        db.upsert(self.conn, [edge, act(8, "2026-11-20")])
        stored = db.all_activities(self.conn)
        fetch = lambda since: [a for a in stored if since is None or a["start_date_local"][:10] >= since.isoformat()]
        sync(self.conn, fetch, TODAY)
        self.assertEqual({a["id"] for a in db.all_activities(self.conn)}, {7, 8})

    def test_demo_is_deterministic_and_fake(self):
        a, b = demo_activities(TODAY), demo_activities(TODAY)
        self.assertEqual(a, b)
        self.assertGreater(len(a), 50)
        self.assertTrue(all(x["id"] >= 10**9 for x in a))


if __name__ == "__main__":
    unittest.main()
