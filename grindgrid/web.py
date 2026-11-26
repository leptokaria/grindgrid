"""HTTP server: SVG grid page and JSON for the widget."""
import html
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from grindgrid import db
from grindgrid.days import GROUPS, build_days
from grindgrid.sync import db_path, today_in

THEMES = ("binary", "intensity", "sports")
# keep in sync with widget/grindgrid.js
EMPTY = "#9aa4b140"
BINARY = "#2fbf71"
SHADES = ["#26c1654d", "#26c16585", "#26c165bb", "#26c165"]  # alpha ramp reads right on light and dark
SPORT_COLORS = {"run": "#ff6b3d", "ride": "#3d8bff", "strength": "#a35cff",
                "swim": "#16c1c8", "walk": "#7cc35a", "other": "#e5b52b"}
LABELS = {"run": "bieganie", "ride": "rower", "strength": "siła", "swim": "pływanie",
          "walk": "chodzenie", "other": "inne"}
CELL, GAP = 12, 3


def day_color(day: dict, theme: str) -> str | None:
    if day["future"]:
        return None
    if day["level"] == 0:
        return EMPTY
    if theme == "intensity":
        return SHADES[day["level"] - 1]
    if theme == "sports":
        return SPORT_COLORS[day["sport_group"]]
    return BINARY


def render_svg(days: list[dict], theme: str) -> str:
    step = CELL + GAP
    weeks = (len(days) + 6) // 7
    cells = []
    for i, d in enumerate(days):
        color = day_color(d, theme)
        if color is None:
            continue
        tip = f"{d['date']}: {d['seconds'] // 60} min"
        cells.append(f'<rect x="{i // 7 * step}" y="{i % 7 * step}" width="{CELL}" height="{CELL}" rx="2" '
                     f'fill="{color}"><title>{tip}</title></rect>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{weeks * step}" height="{7 * step}" '
            f'role="img" aria-label="training grid">{"".join(cells)}</svg>')


def legend(theme: str) -> str:
    if theme == "sports":
        items = [(SPORT_COLORS[g], LABELS[g]) for g in GROUPS]
    elif theme == "intensity":
        items = [(EMPTY, "0"), (SHADES[0], "≤30 min"), (SHADES[1], "≤60"), (SHADES[2], "≤90"), (SHADES[3], "90+")]
    else:
        items = [(EMPTY, "brak"), (BINARY, "trening")]
    return "".join(f'<span><i style="background:{c}"></i>{html.escape(t)}</span>' for c, t in items)


PAGE = """<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>grindgrid</title>
<style>
body{{font:15px system-ui,sans-serif;margin:2rem;background:#fff;color:#1f2328}}
@media(prefers-color-scheme:dark){{body{{background:#0d1117;color:#e6edf3}}}}
nav a{{margin-right:1rem;color:inherit}} nav a.on{{font-weight:700}}
.grid{{overflow-x:auto;margin:1rem 0}} .legend span{{margin-right:1rem}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:4px;vertical-align:-1px}}
</style>
<h1>grindgrid</h1><nav>{nav}</nav><div class="grid">{svg}</div><div class="legend">{legend}</div>
<p>{active} dni z treningiem w ostatnich 12 miesiącach</p></html>"""


def page(days: list[dict], theme: str) -> str:
    nav = "".join(f'<a href="/?theme={t}"{" class=on" if t == theme else ""}>{t}</a>' for t in THEMES)
    active = sum(1 for d in days if d["level"])
    return PAGE.format(nav=nav, svg=render_svg(days, theme), legend=legend(theme), active=active)


def app_days(conn, tz: str) -> list[dict]:
    return build_days(db.all_activities(conn), today_in(tz))


class Handler(BaseHTTPRequestHandler):
    def send(self, status: int, body: str, ctype="text/html; charset=utf-8", headers=None):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(url.query))
        if url.path in ("/", "/api/days"):
            days = app_days(db.connect(db_path()), os.environ.get("TZ", "Europe/Warsaw"))
            if url.path == "/":
                theme = q.get("theme") if q.get("theme") in THEMES else "binary"
                return self.send(200, page(days, theme))
            body = {"days": days, "generated": datetime.now(timezone.utc).isoformat()}
            return self.send(200, json.dumps(body), "application/json")
        self.send(404, "not found")

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    make_server("0.0.0.0", 8080).serve_forever()


if __name__ == "__main__":
    main()
