#!/usr/bin/env python
"""Operator CLI for per-user data requests and retention.

    python scripts/user_data.py summarize <user_id>
    python scripts/user_data.py export    <user_id> [--out FILE]
    python scripts/user_data.py delete    <user_id> [--confirm]
    python scripts/user_data.py retention [--confirm]
    python scripts/user_data.py audit

Deletion and retention are dry runs unless `--confirm` is passed — they print
what they *would* remove and exit. There is no undo once confirmed.

`summarize` is the one to reach for during an incident: it answers "whose data
was affected, and which categories" without dumping the data itself.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.user_data_registry import (  # noqa: E402
    apply_retention,
    audit_coverage,
    export_user,
    purge_user,
    summarize_user,
)


def _print_counts(counts: dict, verb: str) -> None:
    if not counts:
        print(f"No rows to {verb}.")
        return
    width = max(len(t) for t in counts)
    total = 0
    for table, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        if n < 0:
            print(f"  {table:<{width}}  ERROR — see logs")
            continue
        total += n
        print(f"  {table:<{width}}  {n}")
    print(f"  {'TOTAL':<{width}}  {total}")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("summarize", "export", "delete"):
        p = sub.add_parser(name)
        p.add_argument("user_id")
        if name == "export":
            p.add_argument("--out", help="write JSON here instead of stdout")
        if name == "delete":
            p.add_argument("--confirm", action="store_true",
                           help="actually delete (default is a dry run)")

    p = sub.add_parser("retention")
    p.add_argument("--confirm", action="store_true",
                   help="actually delete (default is a dry run)")
    sub.add_parser("audit")

    args = ap.parse_args()

    if args.cmd == "audit":
        missing = audit_coverage()
        if missing:
            print("UNCLASSIFIED TABLES — user data may exist outside the registry:")
            for t in missing:
                print(f"  {t}")
            return 1
        print("All tables are classified.")
        return 0

    if args.cmd == "summarize":
        counts = await summarize_user(args.user_id)
        print(f"Data held for {args.user_id}:")
        _print_counts(counts, "report")
        return 0

    if args.cmd == "export":
        data = await export_user(args.user_id)
        blob = json.dumps(data, indent=2, default=str)
        if args.out:
            Path(args.out).write_text(blob)
            print(f"Wrote {args.out} ({len(blob):,} bytes).")
            print("Contains decrypted credentials and holdings — deliver over a "
                  "channel the customer nominated, then remove the file.")
        else:
            print(blob)
        return 0

    if args.cmd == "delete":
        counts = await purge_user(args.user_id, dry_run=not args.confirm)
        mode = "Deleted" if args.confirm else "Would delete (dry run)"
        print(f"{mode} for {args.user_id}:")
        _print_counts(counts, "delete")
        if not args.confirm:
            print("\nRe-run with --confirm to apply. This cannot be undone.")
        else:
            print("\nStill outstanding: Supabase Auth identity, Supabase Storage "
                  "objects, and subprocessor-held copies (docs/compliance/subprocessors.md).")
        return 0

    if args.cmd == "retention":
        counts = await apply_retention(dry_run=not args.confirm)
        mode = "Deleted" if args.confirm else "Would delete (dry run)"
        print(f"{mode} under the retention schedule:")
        _print_counts(counts, "delete")
        if not args.confirm:
            print("\nRe-run with --confirm to apply.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
