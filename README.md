# India Job-Loss Tracker

A self-updating web dashboard that tracks **job losses across India**, compiled
automatically from verified news reports — broken down by **sector**, **region**,
and **location**, with **AI-related layoffs flagged**.

It runs itself: a weekly GitHub Action fetches the latest layoff news, uses
Claude to extract clean structured records, commits the updated dataset, and
republishes the dashboard. It keeps going until you stop it (disable the
workflow).

```
news (Google News RSS)  →  Claude extraction  →  data/layoffs.json  →  dashboard (GitHub Pages)
        fetch.py              extract.py            store.py              web/
```

## How it works

| Piece | What it does |
|------|--------------|
| `ingest/fetch.py` | Pulls candidate articles from Google News RSS (India edition) for a curated set of layoff queries. Free, no API key. |
| `ingest/extract.py` | Sends each article to **Claude** (structured outputs) to extract company, sector, headcount, city/state/region, AI-relatedness, and a summary. Falls back to a keyword heuristic if no API key is set. |
| `ingest/store.py` | De-duplicates and merges records into `web/data/layoffs.json` (the canonical store the dashboard reads). |
| `ingest/pipeline.py` | Orchestrator with `run` (latest news) and `backfill` (historical) modes. |
| `web/` | Static dashboard — KPIs, time series, sector/region/state charts, a city map, and a searchable table. Chart.js + Leaflet, no build step. |
| `.github/workflows/update-and-deploy.yml` | Weekly cron that runs the pipeline, commits data, and deploys the dashboard to GitHub Pages. |

## One-time setup

By default the builder runs in **free heuristic mode** — no API key, no credits.

1. **Merge this to your default branch (`main`).** GitHub only runs scheduled
   workflows on the default branch, so the weekly cron won't fire from a feature
   branch.
2. **Enable GitHub Pages**: `Settings → Pages → Build and deployment → Source: GitHub Actions`.
3. *(Optional)* **Seed historical data**: go to `Actions → Update data & deploy
   → Run workflow`, choose **backfill**, set the start month (default `2023-01`),
   and run it once. Coverage for older months depends on what free news search
   still returns.

### Optional: upgrade to Claude extraction (better data quality)

Heuristic mode is keyword-based and noisier. To switch on Claude extraction —
which fills in sector, location, headcount, and AI-relatedness far more
accurately — add **both** of these in repo settings (no code change needed):

- a repository **secret** `ANTHROPIC_API_KEY` (from <https://console.anthropic.com>)
- a repository **variable** `USE_CLAUDE` set to `true`
  (`Settings → Secrets and variables → Actions → Variables`)

*(Optionally also set variable `EXTRACTION_MODEL = claude-haiku-4-5` to cut cost
on large batches.)* Remove the variable to drop back to free mode anytime.

After that it runs on its own every Monday. Your dashboard lives at
`https://<your-username>.github.io/<repo>/`.

**To stop it:** disable the workflow in the Actions tab (or delete the schedule).

## Run it locally

```bash
pip install -r ingest/requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # omit to use the heuristic fallback

# Fetch & ingest the latest news:
python -m ingest.pipeline run

# Or seed history since 2023:
python -m ingest.pipeline backfill --since 2023-01

# Preview the dashboard (serve web/ so fetch() works):
python -m http.server -d web 8000
# then open http://localhost:8000
```

Useful flags: `--no-llm` (skip Claude, use heuristics), `--max-articles N` (cap
work for a quick test).

## Notes on data quality

- **Sources are public news reports.** Headcounts reflect the numbers stated in
  articles; they're left blank when unspecified. Treat this as an aggregation
  tool, not an official labour statistic.
- The model is told to be conservative — hiring news, opinion pieces, and purely
  global layoffs with no India angle are filtered out.
- Each record keeps its `source_url`, so every figure is traceable.
- The dashboard ships with a clearly-labelled **synthetic sample dataset**
  (`web/data/sample.json`) so you can see it working before the first real run —
  click *"Preview with sample data."*

## Customising

- **Search coverage**: edit `SEARCH_QUERIES` / `BACKFILL_QUERIES` in
  `ingest/config.py`.
- **Sector / region taxonomy**: edit `SECTORS` / `REGIONS` (and the
  `STATE_TO_REGION` / `CITY_INFO` maps) in `ingest/config.py`.
- **Update frequency**: change the `cron` in the workflow.
