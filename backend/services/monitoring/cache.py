"""In-memory TTL cache with per-key single-flight locking.

The portfolio digest (per-user, 10 min) and the move explainer (per-symbol,
20 min, with drift invalidation + a size bound) carried byte-identical copies
of this. One implementation now, parametrized by TTL and an optional size bound;
callers pass a `validate(meta)` predicate for extra invalidation (e.g. the
explainer drops an entry when the live price has drifted from the cached one).
"""
import asyncio
import time
from typing import Any, Callable, Dict, Optional


class TTLCache:
    def __init__(self, ttl_seconds: float, max_entries: Optional[int] = None,
                 prune_batch: int = 100):
        self._ttl = ttl_seconds
        self._max = max_entries
        self._prune_batch = prune_batch
        self._data: Dict[Any, dict] = {}  # key -> {at, value, meta}
        self._locks: Dict[Any, asyncio.Lock] = {}

    def get(self, key: Any, *, validate: Optional[Callable[[Any], bool]] = None) -> Any:
        """The cached value if present, fresh, and (if given) passing `validate`.

        `validate` receives the `meta` stored alongside the value. Returns None
        on a miss — callers must not cache None as a meaningful value.
        """
        entry = self._data.get(key)
        if not entry:
            return None
        if (time.monotonic() - entry["at"]) >= self._ttl:
            return None
        if validate is not None and not validate(entry.get("meta")):
            return None
        return entry["value"]

    def set(self, key: Any, value: Any, *, meta: Any = None) -> None:
        self._data[key] = {"at": time.monotonic(), "value": value, "meta": meta}
        if self._max and len(self._data) > self._max:
            oldest = sorted(self._data.items(), key=lambda kv: kv[1]["at"])[:self._prune_batch]
            for k, _ in oldest:
                self._data.pop(k, None)

    def lock(self, key: Any) -> asyncio.Lock:
        return self._locks.setdefault(key, asyncio.Lock())
