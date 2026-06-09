"""Orchestrate fetch -> extract -> store for the India job-loss tracker.

Usage:
  python -m ingest.pipeline run [--no-llm] [--max-articles N]
  python -m ingest.pipeline backfill [--since 2023-01] [--no-llm] [--max-articles N]

`run` pulls the latest news for the curated queries (intended for the weekly
cron). `backfill` walks historical date windows to seed the archive.
"""

from __future__ import annotations

import argparse
from datetime import date

from . import config, fetch, store
from .extract import extract_candidates


def _quarter_windows(since: str) -> list[tuple[str, str]]:
    """Build (after, before) YYYY-MM-DD windows, one per quarter, since->now."""
    y, m = (int(p) for p in since.split("-")[:2])
    start_q = (m - 1) // 3  # 0..3
    windows: list[tuple[str, str]] = []
    today = date.today()
    year, q = y, start_q
    while True:
        first_month = q * 3 + 1
        after = date(year, first_month, 1)
        if after > today:
            break
        # before = first day of next quarter
        if q == 3:
            before = date(year + 1, 1, 1)
        else:
            before = date(year, first_month + 3, 1)
        windows.append((after.isoformat(), before.isoformat()))
        if q == 3:
            year, q = year + 1, 0
        else:
            q += 1
    return windows


def run(use_llm: bool, max_articles: int | None) -> int:
    print("==> Fetching latest news (Google News RSS)")
    candidates = fetch.fetch_all(config.SEARCH_QUERIES)
    print(f"    {len(candidates)} unique candidate articles")

    print("==> Extracting structured records")
    pairs = extract_candidates(candidates, use_llm=use_llm, max_articles=max_articles)

    print("==> Merging into store")
    records = [store.build_record(c, e) for c, e in pairs]
    dataset = store.load()
    dataset, added = store.merge(dataset, records)
    store.save(dataset)
    print(f"==> Done. Added {added} new record(s); {dataset['meta']['count']} total.")
    return added


def backfill(since: str, use_llm: bool, max_articles: int | None) -> int:
    windows = _quarter_windows(since)
    print(f"==> Backfilling {len(windows)} quarterly windows since {since}")
    candidates = fetch.fetch_backfill(config.BACKFILL_QUERIES, windows)
    print(f"    {len(candidates)} unique candidate articles")

    pairs = extract_candidates(candidates, use_llm=use_llm, max_articles=max_articles)
    records = [store.build_record(c, e) for c, e in pairs]
    dataset = store.load()
    dataset, added = store.merge(dataset, records)
    store.save(dataset)
    print(f"==> Done. Added {added} new record(s); {dataset['meta']['count']} total.")
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description="India job-loss tracker pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Fetch and ingest the latest news")
    p_run.add_argument("--no-llm", action="store_true", help="Use heuristic extraction")
    p_run.add_argument("--max-articles", type=int, default=None)

    p_bf = sub.add_parser("backfill", help="Seed historical data")
    p_bf.add_argument("--since", default="2023-01", help="Start month, YYYY-MM")
    p_bf.add_argument("--no-llm", action="store_true")
    p_bf.add_argument("--max-articles", type=int, default=None)

    args = parser.parse_args()
    if args.command == "run":
        run(use_llm=not args.no_llm, max_articles=args.max_articles)
    elif args.command == "backfill":
        backfill(
            since=args.since,
            use_llm=not args.no_llm,
            max_articles=args.max_articles,
        )


if __name__ == "__main__":
    main()
