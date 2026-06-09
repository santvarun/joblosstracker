"""Fetch candidate layoff articles from Google News RSS.

Google News exposes a free, key-less RSS search endpoint. We scope it to the
India edition (hl=en-IN, gl=IN, ceid=IN:en) and issue our curated queries. Each
returned item becomes a lightweight "candidate" dict that the extractor later
turns into a structured record.
"""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
USER_AGENT = (
    "Mozilla/5.0 (compatible; JobLossTrackerBot/1.0; "
    "+https://github.com/santvarun/joblosstracker)"
)


@dataclass
class Candidate:
    title: str
    summary: str
    link: str
    source_name: str
    published: str | None  # ISO 8601 or None
    query: str


def _feed_url(query: str) -> str:
    params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    return f"{GOOGLE_NEWS_RSS}?{urllib.parse.urlencode(params)}"


def _published_iso(entry) -> str | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if not parsed:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None


def _source_name(entry) -> str:
    src = getattr(entry, "source", None)
    if src and getattr(src, "title", None):
        return src.title
    # Google News appends " - <Source>" to titles; fall back to that.
    title = getattr(entry, "title", "")
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return "Unknown"


def fetch_query(query: str) -> list[Candidate]:
    import feedparser  # imported lazily so extraction/storage work without it

    url = _feed_url(query)
    feed = feedparser.parse(url, agent=USER_AGENT)
    out: list[Candidate] = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        if not title:
            continue
        out.append(
            Candidate(
                title=title,
                summary=getattr(entry, "summary", "").strip(),
                link=getattr(entry, "link", "").strip(),
                source_name=_source_name(entry),
                published=_published_iso(entry),
                query=query,
            )
        )
    return out


def fetch_all(queries: list[str], pause: float = 1.0) -> list[Candidate]:
    """Run every query, de-duplicating on article link as we go."""
    seen_links: set[str] = set()
    results: list[Candidate] = []
    for q in queries:
        try:
            for cand in fetch_query(q):
                if cand.link and cand.link not in seen_links:
                    seen_links.add(cand.link)
                    results.append(cand)
        except Exception as exc:  # network/parse hiccups shouldn't abort the run
            print(f"  ! fetch failed for query {q!r}: {exc}")
        time.sleep(pause)  # be polite to the endpoint
    return results


def fetch_backfill(
    queries: list[str], windows: list[tuple[str, str]], pause: float = 1.0
) -> list[Candidate]:
    """Backfill historical articles using Google News after:/before: operators.

    `windows` is a list of (after_date, before_date) strings in YYYY-MM-DD form.
    """
    seen_links: set[str] = set()
    results: list[Candidate] = []
    for after, before in windows:
        for base in queries:
            q = f"{base} after:{after} before:{before}"
            try:
                for cand in fetch_query(q):
                    if cand.link and cand.link not in seen_links:
                        seen_links.add(cand.link)
                        results.append(cand)
            except Exception as exc:
                print(f"  ! backfill fetch failed for {q!r}: {exc}")
            time.sleep(pause)
    return results


def candidate_to_dict(cand: Candidate) -> dict:
    return asdict(cand)
