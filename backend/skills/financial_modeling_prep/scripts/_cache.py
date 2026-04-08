"""Shared disk cache for FMP API responses (historical data never changes)."""
import json
import os
import hashlib


def cache_key(*parts: str) -> str:
    return hashlib.md5('|'.join(parts).encode()).hexdigest()


def load_cache(cache_dir: str, key: str):
    path = os.path.join(cache_dir, f'{key}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_cache(cache_dir: str, key: str, data) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, f'{key}.json'), 'w') as f:
        json.dump(data, f)
