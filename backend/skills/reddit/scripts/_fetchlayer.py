"""
FetchLayer backend for reddit_api — third-party multi-platform data provider.

Base: POST https://api.fetchlayer.dev/reddit/{endpoint}, Bearer auth, JSON body.
Needs FETCHLAYER_API_KEY. Instant signup (free 30 calls, then ~$0.002/call), no
Responsible Builder approval. FetchLayer scrapes Reddit — fine as the prototype /
discovery backend; the 'official' backend is the production-durable target.

Field shapes below verified against live responses (Aug 2026):
  - search / community-posts -> { items: [ {id, title, author, permalink, url,
    createdAt, flair, score(nullable), commentCount(nullable), previewText, ...} ] }
  - post -> full submission { ..., bodyText, score, commentCount, comments: [...] }
    where each comment = { author, bodyText, score, depth, children:[...replies] }

Returns the same normalized shapes as every other backend; see reddit_api.py.
"""
import os

import requests

BASE = "https://api.fetchlayer.dev/reddit"


def _key() -> str:
    k = os.environ.get("FETCHLAYER_API_KEY")
    if not k:
        raise RuntimeError(
            "FETCHLAYER_API_KEY not set. Get a key at https://fetchlayer.dev (free tier, no card) "
            "and add it to backend/.env."
        )
    return k


def _call(endpoint: str, payload: dict) -> dict:
    resp = requests.post(
        f"{BASE}/{endpoint}",
        json=payload,
        headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def _norm_post(d: dict) -> dict:
    # bodyText populated on the `post` endpoint; previewText on listings.
    return {
        "id": d.get("id"),
        "title": d.get("title"),
        "author": d.get("author"),
        "selftext": d.get("bodyText") or d.get("previewText") or "",
        "score": d.get("score"),
        "num_comments": d.get("commentCount"),
        "created_utc": d.get("createdAt"),
        "flair": d.get("flair"),
        "permalink": d.get("permalink") or d.get("url"),
    }


def _flatten(children, out, max_depth):
    """Depth-first flatten of FetchLayer's nested comment tree (children = replies)."""
    for c in children or []:
        body = c.get("bodyText")
        if body:
            out.append(
                {"author": c.get("author"), "body": body, "score": c.get("score"), "depth": c.get("depth", 0)}
            )
        kids = c.get("children")
        if kids and c.get("depth", 0) < max_depth:
            _flatten(kids, out, max_depth)


def _thread_url(post_ref) -> str:
    # The `post` endpoint needs a full thread URL. Accept a post dict, a URL, or a
    # bare base36 id (which we resolve to reddit's canonical /comments/ URL).
    if isinstance(post_ref, dict):
        u = post_ref.get("permalink") or ""
        if u.startswith("http"):
            return u
        post_ref = post_ref.get("id") or post_ref.get("url") or ""
    s = str(post_ref)
    if s.startswith("http"):
        return s
    return f"https://www.reddit.com/comments/{s}/"


def search_community(subreddit, query, sort="top", time_filter="year", limit=25):
    data = _call("search", {"query": query, "subreddit": subreddit, "sort": sort, "limit": min(limit, 100)})
    return [_norm_post(it) for it in data.get("items", [])]


def get_community_posts(subreddit, sort="top", time_filter="month", limit=25):
    data = _call("community-posts", {"subreddit": subreddit, "sort": sort, "time": time_filter, "limit": min(limit, 100)})
    return [_norm_post(it) for it in data.get("items", [])]


def read_thread(post_ref, comment_limit=100, max_depth=4):
    data = _call("post", {"url": _thread_url(post_ref)})
    post = _norm_post(data)
    comments = []
    _flatten(data.get("comments", []), comments, max_depth)
    post["comments"] = comments[:comment_limit] if comment_limit else comments
    return post
