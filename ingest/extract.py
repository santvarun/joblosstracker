"""Turn raw news candidates into structured layoff records.

Primary path: Claude structured-output extraction (accurate, fills sector /
location / headcount / AI-relatedness). Fallback path: a lightweight keyword
heuristic so the pipeline still produces *something* when no API key is present
(e.g. a fork running without secrets configured).
"""

from __future__ import annotations

import os
import re
from typing import Optional

from pydantic import BaseModel, Field

from .config import REGIONS, SECTORS
from .fetch import Candidate

# Default to the most capable model; override with EXTRACTION_MODEL. For a
# high-volume weekly batch you can set EXTRACTION_MODEL=claude-haiku-4-5 to cut
# extraction cost substantially -- it handles this structured task well.
EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "claude-opus-4-8")

# Articles must look layoff-related before we spend a model call on them.
_LAYOFF_HINT = re.compile(
    r"\b(lay[\s-]?off|laid off|job cut|jobs? cut|retrench|"
    r"sack(?:ed|ing)?|fired|workforce reduc|downsiz|pink slip|"
    r"let go|redundanc|job loss)\w*",
    re.IGNORECASE,
)


class Extraction(BaseModel):
    """Schema Claude fills for a single article."""

    is_india_layoff: bool = Field(
        description=(
            "True only if this article reports an actual layoff / job cut / "
            "retrenchment at a company in India. False for hiring news, "
            "opinion pieces, global layoffs with no India angle, or rumors."
        )
    )
    company: str = Field(description="Name of the company cutting jobs.")
    sector: str = Field(description=f"One of exactly: {', '.join(SECTORS)}")
    headcount: Optional[int] = Field(
        description="Number of employees laid off. Null if not stated."
    )
    city: Optional[str] = Field(
        description="Primary Indian city affected, canonical spelling, or null."
    )
    state: Optional[str] = Field(
        description="Indian state/UT affected, or null."
    )
    region: str = Field(
        description=f"One of exactly: {', '.join(REGIONS)}. Use Pan-India for "
        "nationwide cuts, Unknown if unclear."
    )
    date: str = Field(
        description="Announcement date as YYYY-MM-DD, or YYYY-MM if only the "
        "month is known. Use the article's publish date if the event date "
        "is not stated."
    )
    ai_related: bool = Field(
        description="True if the layoff is attributed -- wholly or partly -- to "
        "AI, automation, or restructuring around AI adoption."
    )
    ai_rationale: Optional[str] = Field(
        description="One short sentence on the AI link, or null if not AI-related."
    )
    summary: str = Field(description="One-sentence neutral summary of the layoff.")
    confidence: float = Field(
        description="0.0-1.0 confidence that the structured fields are correct."
    )


_SYSTEM_PROMPT = f"""You are a precise data extraction system for an India \
job-loss tracker. You read a single news article (title + snippet) and extract \
structured facts about layoffs in India.

Rules:
- Only mark is_india_layoff=true for confirmed layoffs/job cuts/retrenchments at \
a company operating in India. Reject hiring news, generic economic commentary, \
listicles, and purely global layoffs with no India operations affected.
- sector MUST be exactly one of: {', '.join(SECTORS)}.
- region MUST be exactly one of: {', '.join(REGIONS)}.
- Use canonical Indian city names (e.g. Bengaluru, not Bangalore; Mumbai, not \
Bombay; Gurugram, not Gurgaon).
- headcount is the number of people laid off. Null if the article gives no number. \
Do not guess a number.
- Be conservative: when unsure whether it is a real India layoff, set \
is_india_layoff=false."""


def _looks_relevant(cand: Candidate) -> bool:
    text = f"{cand.title} {cand.summary}"
    return bool(_LAYOFF_HINT.search(text))


def _client():
    try:
        import anthropic
    except ImportError:
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        return anthropic.Anthropic()
    except Exception:
        return None


def extract_with_llm(client, cand: Candidate) -> Optional[Extraction]:
    user_text = (
        f"SOURCE: {cand.source_name}\n"
        f"PUBLISHED: {cand.published or 'unknown'}\n"
        f"TITLE: {cand.title}\n"
        f"SNIPPET: {cand.summary or '(no snippet)'}"
    )
    try:
        resp = client.messages.parse(
            model=EXTRACTION_MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    # Cache the (large, stable) taxonomy prompt across articles.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_text}],
            output_format=Extraction,
        )
        return resp.parsed_output
    except Exception as exc:
        print(f"  ! LLM extraction failed: {exc}")
        return None


# --- Heuristic fallback ----------------------------------------------------

_NUM_NEAR_LAYOFF = re.compile(
    r"(\d[\d,]{1,7})\s*(?:\+|plus)?\s*(?:employees|workers|staff|jobs|people|"
    r"roles|positions)?\b[^.]{0,40}?(?:lay|cut|fire|sack|retrench)|"
    r"(?:lay|cut|fire|sack|retrench)\w*[^.]{0,40}?(\d[\d,]{1,7})",
    re.IGNORECASE,
)
_AI_HINT = re.compile(r"\b(AI|artificial intelligence|automation|automat)\w*",
                      re.IGNORECASE)


def _guess_company(title: str) -> str:
    # Strip the trailing " - Source" Google News adds, then take the leading
    # capitalized phrase as a rough company guess.
    head = title.rsplit(" - ", 1)[0]
    m = re.match(r"([A-Z][\w&.]*(?:\s+[A-Z][\w&.]*){0,3})", head)
    return m.group(1).strip() if m else "Unknown"


def extract_heuristic(cand: Candidate) -> Optional[Extraction]:
    text = f"{cand.title} {cand.summary}"
    headcount = None
    m = _NUM_NEAR_LAYOFF.search(text)
    if m:
        raw = next((g for g in m.groups() if g), None)
        if raw:
            try:
                headcount = int(raw.replace(",", ""))
            except ValueError:
                headcount = None
    date = (cand.published or "")[:10] or "unknown"
    return Extraction(
        is_india_layoff=True,  # query already scoped to India layoffs
        company=_guess_company(cand.title),
        sector="Other",
        headcount=headcount,
        city=None,
        state=None,
        region="Unknown",
        date=date if date != "unknown" else "1970-01",
        ai_related=bool(_AI_HINT.search(text)),
        ai_rationale=None,
        summary=cand.title.rsplit(" - ", 1)[0],
        confidence=0.3,
    )


def extract_candidates(
    candidates: list[Candidate], use_llm: bool = True, max_articles: int | None = None
) -> list[tuple[Candidate, Extraction]]:
    """Extract every relevant candidate. Returns (candidate, extraction) pairs."""
    client = _client() if use_llm else None
    if use_llm and client is None:
        print(
            "  ! No ANTHROPIC_API_KEY / anthropic SDK -- falling back to "
            "heuristic extraction (lower quality)."
        )

    relevant = [c for c in candidates if _looks_relevant(c)]
    if max_articles:
        relevant = relevant[:max_articles]
    print(f"  {len(relevant)} relevant of {len(candidates)} candidates")

    out: list[tuple[Candidate, Extraction]] = []
    for i, cand in enumerate(relevant, 1):
        if client is not None:
            ext = extract_with_llm(client, cand)
        else:
            ext = extract_heuristic(cand)
        if ext and ext.is_india_layoff:
            out.append((cand, ext))
        if i % 25 == 0:
            print(f"  ...processed {i}/{len(relevant)}")
    print(f"  {len(out)} confirmed India layoff records")
    return out
