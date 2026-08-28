"""
Reddit community reading — provider-neutral interface.

Callers (e.g. strategy_distiller) use search_community / get_community_posts /
read_thread and never see which provider answered. REDDIT_BACKEND selects the
data source:

  - "official"   -> official Reddit Data API   (REDDIT_CLIENT_ID/SECRET; approval-gated, durable)
  - "fetchlayer" -> FetchLayer third-party API  (FETCHLAYER_API_KEY; instant, paid-per-call)

Every backend returns the SAME normalized shapes:

  post  = { id, title, author, selftext, score, num_comments, created_utc, flair, permalink }
  thread = post + { comments: [ { author, body, score, depth } ] }

So switching providers (or flipping to 'official' once approved) is a one-env-var
change with zero downstream edits. See docs/community-strategies-research.md §3.
"""
import os


def active_backend() -> str:
    return (os.environ.get("REDDIT_BACKEND") or "official").strip().lower()


def _backend():
    name = active_backend()
    if name == "official":
        from . import _official as b
    elif name == "fetchlayer":
        from . import _fetchlayer as b
    else:
        raise RuntimeError(f"Unknown REDDIT_BACKEND={name!r}; use 'official' or 'fetchlayer'.")
    return b


def search_community(subreddit, query, sort="top", time_filter="year", limit=25):
    """Search within one community. Returns a list of normalized post dicts."""
    return _backend().search_community(subreddit, query, sort=sort, time_filter=time_filter, limit=limit)


def get_community_posts(subreddit, sort="top", time_filter="month", limit=25):
    """Fetch a community's listing (hot|new|top|rising). Returns normalized post dicts."""
    return _backend().get_community_posts(subreddit, sort=sort, time_filter=time_filter, limit=limit)


def read_thread(post_ref, comment_limit=100, max_depth=4):
    """
    Fetch a full thread (post + comments). `post_ref` may be a post dict from a
    search/listing result, a reddit URL, or a base36 post id.
    """
    return _backend().read_thread(post_ref, comment_limit=comment_limit, max_depth=max_depth)
