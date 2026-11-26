import json
import os
import tempfile
import unittest

from grindgrid import strava


class StravaTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "tokens.json")

    def tearDown(self):
        self.dir.cleanup()

    def save(self, **tok):
        with open(self.path, "w") as f:
            json.dump(tok, f)

    def test_authorize_url_has_scope(self):
        url = strava.authorize_url("123", "http://localhost:8080/callback", "nonce1")
        self.assertIn("scope=activity%3Aread_all", url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback", url)
        self.assertIn("client_id=123", url)
        self.assertIn("state=nonce1", url)

    def test_exchange_code_saves_tokens_private(self):
        post = lambda url, data: {"access_token": "a", "refresh_token": "r", "expires_at": 99, "athlete": {}}
        strava.exchange_code("1", "s", "code", self.path, post=post)
        with open(self.path) as f:
            self.assertEqual(json.load(f), {"access_token": "a", "refresh_token": "r", "expires_at": 99})
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_refresh_saves_rotated_refresh_token(self):
        self.save(access_token="old", refresh_token="r1", expires_at=1000)
        sent = []

        def post(url, data):
            sent.append(data)
            return {"access_token": "fresh", "refresh_token": "new", "expires_at": 99999}

        self.assertEqual(strava.access_token("1", "s", self.path, now=lambda: 2000, post=post), "fresh")
        self.assertEqual(sent[0]["refresh_token"], "r1")
        self.assertEqual(sent[0]["grant_type"], "refresh_token")
        with open(self.path) as f:
            self.assertEqual(json.load(f)["refresh_token"], "new")

    def test_valid_token_not_refreshed(self):
        self.save(access_token="ok", refresh_token="r1", expires_at=10**10)
        post = lambda url, data: self.fail("should not refresh")
        self.assertEqual(strava.access_token("1", "s", self.path, now=lambda: 2000, post=post), "ok")

    def test_pagination_stops_on_empty_page(self):
        raw = {"id": 1, "start_date_local": "2026-11-20T07:00:00Z", "sport_type": "Run",
               "moving_time": 10, "elapsed_time": 12, "name": "Morning", "map": {}}
        pages = [[raw, dict(raw, id=2)], [dict(raw, id=3)], []]
        calls = []

        def get(url, headers):
            calls.append(url)
            return pages[len(calls) - 1]

        got = strava.fetch_activities("tok", 1700000000, get=get)
        self.assertEqual([a["id"] for a in got], [1, 2, 3])
        self.assertEqual(set(got[0]), {"id", "start_date_local", "sport_type", "moving_time", "elapsed_time"})
        self.assertEqual(len(calls), 3)
        self.assertIn("after=1700000000", calls[0])
        self.assertIn("per_page=200", calls[0])

    def test_full_fetch_has_no_after(self):
        got = strava.fetch_activities("tok", None, get=lambda url, h: self.assertNotIn("after", url) or [])
        self.assertEqual(got, [])


if __name__ == "__main__":
    unittest.main()
