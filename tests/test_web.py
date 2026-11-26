import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from grindgrid import sync, web


class WebTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"GRINDGRID_DATA": self.dir.name})
        self.env.start()
        self.server = web.make_server("127.0.0.1", 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.env.stop()
        self.dir.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as r:
            return r.status, r.read().decode()

    def test_empty_install_renders(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("<svg", body)
        status, body = self.get("/api/days")
        days = json.loads(body)["days"]
        self.assertEqual(len(days), 371)
        self.assertTrue(all(d["level"] == 0 for d in days))

    def test_api_days_after_demo(self):
        sync.main(["--demo"])
        days = json.loads(self.get("/api/days")[1])["days"]
        self.assertTrue(any(d["level"] > 0 for d in days))

    def test_unknown_theme_falls_back(self):
        self.assertEqual(self.get("/?theme=nope")[0], 200)

    def test_unknown_path_404(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.get("/nope")
        self.assertEqual(e.exception.code, 404)


class ColorTest(unittest.TestCase):
    def test_colors_differ_by_theme(self):
        day = {"date": "2026-11-24", "seconds": 1200, "level": 1, "sport_group": "strength", "future": False}
        colors = {t: web.day_color(day, t) for t in web.THEMES}
        self.assertEqual(len(set(colors.values())), 3)
        self.assertIsNone(web.day_color(dict(day, future=True), "binary"))
        empty = dict(day, level=0, seconds=0, sport_group=None)
        self.assertEqual(len({web.day_color(empty, t) for t in web.THEMES}), 1)


    def test_accent_recolors_binary_and_intensity_only(self):
        day = {"date": "2026-11-24", "seconds": 1200, "level": 1, "sport_group": "run", "future": False}
        ember = web.ACCENTS["ember"]
        self.assertEqual(web.day_color(day, "binary", "ember"), ember)
        self.assertEqual(web.day_color(day, "intensity", "ember"), ember + "4d")
        self.assertEqual(web.day_color(dict(day, level=4), "intensity", "ember"), ember)
        self.assertEqual(web.day_color(day, "sports", "ember"), web.day_color(day, "sports"))
        self.assertEqual(len(web.ACCENTS), 8)


class AccentPageTest(WebTest):
    def test_accent_query_changes_page_colors(self):
        sync.main(["--demo"])
        body = self.get("/?accent=ember")[1]
        self.assertIn(web.ACCENTS["ember"], body)
        self.assertNotIn('fill="' + web.ACCENTS["green"] + '"', body)  # grid cells, not the picker

    def test_default_and_unknown_accent_are_teal(self):
        sync.main(["--demo"])
        for path in ("/", "/?accent=nope"):
            self.assertIn('fill="' + web.ACCENTS["teal"] + '"', self.get(path)[1])


if __name__ == "__main__":
    unittest.main()
