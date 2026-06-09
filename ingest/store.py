"""Persist layoff records to the canonical JSON store the dashboard reads.

The store lives at web/data/layoffs.json so GitHub Pages can serve it directly.
Records are de-duplicated on a stable id derived from company + month + city,
and we also skip any article URL we've already ingested.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone

from .config import SECTORS
from .extract import Extraction
from .fetch import Candidate
from .geo import resolve

# Default canonical location; overridable for tests / alternate layouts.
DATA_PATH = os.environ.get(
    "DATA_PATH",
    os.path.join(os.path.dirname(__file__), "..", "web", "data", "layoffs.json"),
)


def _normalize_company(name: str) -> str:
    name = name.lower()
    name = re.sub(r"\b(pvt|private|ltd|limited|inc|llp|technologies|technology|"
                  r"solutions|india|labs|corp|company)\b", "", name)
    name = re.sub(r"[^a-z0-9]", "", name)
    return name


def _month(date: str) -> str:
    return (date or "")[:7]  # YYYY-MM


def record_id(company: str, date: str, city: str | None) -> str:
    basis = f"{_normalize_company(company)}|{_month(date)}|{(city or '').lower()}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def build_record(cand: Candidate, ext: Extraction) -> dict:
    geo = resolve(ext.city, ext.state, ext.region)
    sector = ext.sector if ext.sector in SECTORS else "Other"
    rid = record_id(ext.company, ext.date, geo["city"])
    return {
        "id": rid,
        "company": ext.company.strip(),
        "sector": sector,
        "headcount": ext.headcount,
        "city": geo["city"],
        "state": geo["state"],
        "region": geo["region"],
        "lat": geo["lat"],
        "lng": geo["lng"],
        "date": ext.date,
        "month": _month(ext.date),
        "ai_related": bool(ext.ai_related),
        "ai_rationale": ext.ai_rationale,
        "summary": ext.summary.strip(),
        "source_name": cand.source_name,
        "source_url": cand.link,
        "source_published": cand.published,
        "confidence": round(float(ext.confidence), 2),
        "extracted_by": "heuristic" if ext.confidence <= 0.3 else "llm",
        "first_seen": datetime.now(timezone.utc).isoformat(),
    }


def load() -> dict:
    if not os.path.exists(DATA_PATH):
        return {"meta": {}, "records": []}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save(dataset: dict) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    records = dataset["records"]
    ai_records = [r for r in records if r.get("ai_related")]
    dataset["meta"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "ai_related_count": len(ai_records),
        "total_headcount": sum(r.get("headcount") or 0 for r in records),
        "version": 1,
        "note": (
            "Layoffs in India compiled from verified news reports via an "
            "automated, self-updating pipeline. Headcounts reflect figures "
            "stated in source articles; null where unspecified."
        ),
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)


def merge(dataset: dict, new_records: list[dict]) -> tuple[dict, int]:
    """Merge new records into the dataset. Returns (dataset, num_added)."""
    by_id = {r["id"]: r for r in dataset["records"]}
    seen_urls = {r.get("source_url") for r in dataset["records"] if r.get("source_url")}
    added = 0
    for rec in new_records:
        if rec.get("source_url") and rec["source_url"] in seen_urls:
            continue
        existing = by_id.get(rec["id"])
        if existing is None:
            by_id[rec["id"]] = rec
            added += 1
            if rec.get("source_url"):
                seen_urls.add(rec["source_url"])
        else:
            # Same event already known: enrich missing fields, prefer a stated
            # headcount and better geo over nulls.
            if existing.get("headcount") is None and rec.get("headcount") is not None:
                existing["headcount"] = rec["headcount"]
            for field in ("city", "state", "lat", "lng"):
                if existing.get(field) is None and rec.get(field) is not None:
                    existing[field] = rec[field]
            if existing.get("region") in (None, "Unknown") and rec.get("region"):
                existing["region"] = rec["region"]
            if not existing.get("ai_related") and rec.get("ai_related"):
                existing["ai_related"] = True
                existing["ai_rationale"] = rec.get("ai_rationale")
    # Keep records sorted newest-first for a stable, reviewable diff.
    dataset["records"] = sorted(
        by_id.values(), key=lambda r: (r.get("month") or "", r.get("first_seen") or ""),
        reverse=True,
    )
    return dataset, added
