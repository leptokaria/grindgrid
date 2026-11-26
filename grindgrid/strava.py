"""Minimal Strava API client: OAuth, token refresh, activity listing."""
import json
import os
import time
import urllib.parse
import urllib.request

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
FIELDS = ("id", "start_date_local", "sport_type", "moving_time", "elapsed_time")


def _post(url: str, data: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:  # raises HTTPError on non-2xx
        return json.load(r)


def _get(url: str, headers: dict) -> list:
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def authorize_url(client_id: str, redirect_uri: str) -> str:
    return AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": "activity:read_all", "approval_prompt": "auto"})


def _save(token_path: str, resp: dict) -> None:
    tok = {k: resp[k] for k in ("access_token", "refresh_token", "expires_at")}
    fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(tok, f)


def exchange_code(client_id, client_secret, code, token_path: str, post=_post) -> None:
    _save(token_path, post(TOKEN_URL, {"client_id": client_id, "client_secret": client_secret,
                                       "code": code, "grant_type": "authorization_code"}))


def access_token(client_id, client_secret, token_path, now=time.time, post=_post) -> str:
    with open(token_path) as f:
        tok = json.load(f)
    if tok["expires_at"] - 60 > now():
        return tok["access_token"]
    resp = post(TOKEN_URL, {"client_id": client_id, "client_secret": client_secret,
                            "refresh_token": tok["refresh_token"], "grant_type": "refresh_token"})
    _save(token_path, resp)  # Strava rotates the refresh token: losing it breaks auth
    return resp["access_token"]


def fetch_activities(token: str, after: int | None, get=_get) -> list[dict]:
    out, page = [], 1
    while True:
        params = {"per_page": 200, "page": page}
        if after is not None:
            params["after"] = after
        batch = get(ACTIVITIES_URL + "?" + urllib.parse.urlencode(params), {"Authorization": f"Bearer {token}"})
        if not batch:
            return out
        out += [{k: a.get(k) for k in FIELDS} for a in batch]
        page += 1
