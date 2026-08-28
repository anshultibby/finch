"""
Official Reddit Data API backend for reddit_api.

Read-only application-only OAuth (client_credentials) with a *script* app's
client_id/secret — no user login for public reads. Sanctioned path, free for
non-commercial use (~100 q/min). Requires REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET.
App creation is currently gated behind Reddit's Responsible Builder Policy — until
approved, use the 'fetchlayer' backend (REDDIT_BACKEND=fetchlayer).

Returns the same normalized shapes as every other backend; see reddit_api.py.
"""
import os
import time

import requests

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
USER_AGENT = "finch:community-strategies:v0.1 (by /u/finch-app)"

_token = {"value": None, "exp": 0.0}


def _get_token() -> str:
    cid = os.environ.get("REDDIT_CLIENT_ID")
    sec = os.environ.get("REDDIT_CLIENT_SECRET")
    if not cid or not sec:
        raise RuntimeError(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set. Register a 'script' app at "
            "https://reddit.com/prefs/apps and add both to backend/.env — or set "
            "REDDIT_BACKEND=fetchlayer to use the third-party provider instead."
        )
    now = time.time()
    if _token["value"] and now < _token["exp"] - 30:
        return _token["value"]
    resp = requests.post(
        TOKEN_URL,
        auth=(cid, sec),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    tok = resp.json()
    _token["value"] = tok["access_token"]
    _token["exp"] = now + float(tok.get("expires_in", 3600))
    return _token["value"]


def _get(path: str, params: dict = None) -> dict:
    token = _get_token()
    resp = requests.get(
        f"{API}{path}",
        params=params or {},
        headers={"Authorization": f"bearer {token}", "User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _norm_post(d: dict) -> dict:
    return {
        "id": d.get("id"),
        "title": d.get("title"),
        "author": d.get("author"),
        "selftext": d.get("selftext", ""),
        "score": d.get("score"),
        "num_comments": d.get("num_comments"),
        "created_utc": d.get("created_utc"),
        "flair": d.get("link_flair_text"),
        "permalink": f"https://reddit.com{d.get('permalink', '')}",
    }


def _extract_id(post_ref) -> str:
    """Accept a post dict (from search/list), a reddit URL, or a base36 id."""
    if isinstance(post_ref, dict):
        if post_ref.get("id"):
            return post_ref["id"]
        post_ref = post_ref.get("permalink") or post_ref.get("url") or ""
    s = str(post_ref)
    if "/comments/" in s:
        parts = [p for p in s.split("/") if p]
        if "comments" in parts:
            i = parts.index("comments")
            if i + 1 < len(parts):
                return parts[i + 1]
    return s


def search_community(subreddit, query, sort="relevance", time_filter="year", limit=25):
    data = _get(
        f"/r/{subreddit}/search",
        {"q": query, "restrict_sr": "on", "sort": sort, "t": time_filter, "limit": min(limit, 100)},
    )
    return [_norm_post(c["data"]) for c in data.get("data", {}).get("children", [])]


def get_community_posts(subreddit, sort="top", time_filter="month", limit=25):
    params = {"limit": min(limit, 100)}
    if sort == "top":
        params["t"] = time_filter
    data = _get(f"/r/{subreddit}/{sort}", params)
    return [_norm_post(c["data"]) for c in data.get("data", {}).get("children", [])]


def read_thread(post_ref, comment_limit=100, max_depth=4):
    post_id = _extract_id(post_ref)
    data = _get(f"/comments/{post_id}", {"limit": comment_limit, "depth": max_depth})
    post = _norm_post(data[0]["data"]["children"][0]["data"])
    comments = []
    for c in data[1]["data"]["children"]:
        cd = c.get("data", {})
        body = cd.get("body")
        if body:
            comments.append(
                {"author": cd.get("author"), "body": body, "score": cd.get("score"), "depth": cd.get("depth", 0)}
            )
    post["comments"] = comments
    return post
