# Market Intelligence Agent

A pipeline and dashboard that compares image-to-video AI models (Kling 3.0 and its competitors) and the API providers that host them (fal.ai and alternatives), so cost, quality and limits can be seen side by side.

Web pages (pricing, docs, reviews) are collected with FireCrawl, an LLM (DeepSeek) turns the raw text into structured records, a verification step checks them, and the results are stored in Postgres, served by a FastAPI backend and shown in a React dashboard.

## What it does

- **Models**: price per second, reference-image limit, prompt limit (in **characters**), multi-shot support, review summary (`quality_notes`) and, when a review states one, a numeric `quality_score`.
- **API providers**: short, objective pricing and stability summaries, and `uptime_pct` = the **measured** 90-day API uptime from the provider's official status page (marketing/SLA claims are kept out of that field).
- **Dashboard**: weighted ranking (weights adjustable live), comparison table, model detail, provider table. Every value shows its source and collection date, or is marked "not verified" (`*`).
- **Data quality**: nothing the LLM extracts is trusted on its own. See [Data quality](#data-quality).
- **Merge rules**: the same model can be fed by several sources. Identity (name, provider) is first-write-wins, so a later mismatched source cannot rename a record. Other facts are also first-write-wins, except that a newly **verified** value (one with evidence) may update them, and the change is printed. Free-text fields (`quality_notes`, `notes`) accumulate.

## Architecture

```
FireCrawl (scrape / search) -> DeepSeek (extraction + quotes) -> verify.py -> Postgres
                                                                                |
                                       React dashboard  <-  FastAPI (/api/models, /api/providers, /api/history)
```

FireCrawl only *collects* the raw page text. DeepSeek *extracts* fields from it. `verify.py` then checks the extraction in plain code before anything is saved. Plain-text pages (`.txt`, `.json`, `.md`, e.g. fal.ai's `llms.txt`) are downloaded with a normal HTTP request, so they cost no FireCrawl credits.

| Path | Role |
|---|---|
| `src/market_intel/sources.py` | Fetch a URL or search the web (FireCrawl, or plain HTTP for text pages) |
| `src/market_intel/extract.py` | LLM extraction with forced tool use, validated by Pydantic |
| `src/market_intel/schema.py` | Pydantic models (`ModelComparison`, `ProviderComparison`, and the `*Extraction` variants that carry evidence quotes) |
| `src/market_intel/verify.py` | Deterministic verification of extracted facts (quotes, numbers, ranges, target identity) |
| `src/market_intel/store.py` | Persistence, merge rules and evidence storage |
| `src/market_intel/db.py` | SQLAlchemy models (`models`, `providers`, `field_evidence`) and engine |
| `src/market_intel/api.py` | FastAPI app |
| `src/market_intel/run_pipeline.py` | CLI entry point for the collection pipeline |
| `scripts/export_static.py` | Builds a single self-contained HTML snapshot of the dashboard |
| `frontend/` | React (Vite) dashboard |
| `tests/` | pytest suite (SQLite, no network or API keys needed) |

## Running it

Requirements: Docker, and API keys for [DeepSeek](https://platform.deepseek.com) and [FireCrawl](https://www.firecrawl.dev).

```bash
cp .env.example .env        # then fill in the two API keys
docker compose up -d --build
```

- Dashboard: http://localhost:5173
- API: http://localhost:8000/api/models (interactive docs at `/docs`)
- Postgres is exposed on host port 5433.

### Collecting data

Run inside the API container:

```bash
# Model page (plain-text pages like llms.txt need no FireCrawl credits)
docker compose exec api python -m market_intel.run_pipeline url "https://fal.ai/models/bytedance/seedance-2.0/image-to-video/llms.txt" seedance-2.0

# Search the web for a review of a model
docker compose exec api python -m market_intel.run_pipeline quality '"Veo 3.1" Google DeepMind video generation review 2026' veo-3.1

# Search the web for an API provider
docker compose exec api python -m market_intel.run_pipeline provider '"Baseten.co" model inference platform pricing uptime' baseten

# Measured uptime from an official status page: <status URL> <provider name> <provider_key>
docker compose exec api python -m market_intel.run_pipeline status https://status.fal.ai fal.ai fal-ai
```

The last argument is a stable key that identifies the record, so several sources can be merged into the same model. It is also the **expected identity**: if the page or the extraction is about a different model/provider than the key, the whole collection is rejected and nothing is saved.

Each run prints the source URL, the fields that passed (`OK`), the ones dropped and why (`DESCARTADO`), and any stored value that changed (`ATUALIZADO`).

Prefer official sources: fal.ai's `llms.txt` per model, the creators' API docs for limits, and official status pages for uptime.

### Scheduled collection

`scripts/run_collection.py` walks `targets.json` — a curated list of **fixed URLs**, never search — and re-collects each one with `facts_only=True` (prices, limits, multi-shot, uptime; `quality_notes`/`notes` are left untouched, or they'd grow with a slightly reworded duplicate every run). Each target is isolated: one bad target doesn't stop the others. The script exits non-zero only if a whole target was rejected (wrong page/model), not for an individual dropped field, which is normal.

```bash
python scripts/run_collection.py            # local run against whatever DATABASE_URL points to
```

`.github/workflows/collect.yml` runs this daily at 09:00 UTC (`workflow_dispatch` also allows a manual run from the Actions tab), then rebuilds the frontend, regenerates the static snapshot and publishes it to GitHub Pages. It needs three repository secrets — `DATABASE_URL` (pointing at a reachable Postgres, e.g. Supabase's session-pooler URL), `DEEP_SEEK_API_KEY`, `FIRECRAWL_API_KEY` — and, once, the repo's **Settings > Pages > Source** set to "GitHub Actions".

Some sources are deliberately left out of `targets.json` (see the `_excluded_*_comment` keys in the file for why): a wrong review search result would corrupt a record with nobody watching, and some official pages don't carry a stable, comparable number even when the text "verifies" cleanly:
- **Sora 2**: OpenAI discontinued the product; needs a human decision (mark discontinued / remove from ranking), not an automatic price refresh.
- **Luma Ray 3.2**: the only fal.ai page found is for Ray 2, a different version — correctly rejected every time, so left out to avoid noise until a real Ray 3.2 source turns up.
- **Together AI's status page**: it lists uptime per hosted *model*, not a platform component. Our "use the lowest one" rule then quotes a different model's number every run — technically verified (real quote, real number) but not a stable reliability signal. Needs a rule that reads *all* the per-model rows and averages them in code, not an LLM picking one.
- **Replicate's status page**: no uptime percentage at all, only incident days.

### Sharing a snapshot

To show the dashboard to someone without running anything, build a single HTML file with the current data embedded:

```bash
cd frontend && npm run build && cd ..
python scripts/export_static.py      # -> export/market-intel-snapshot.html (git-ignored)
```

It opens by double-click, needs no server or internet, and shows the snapshot date in the top bar.

### Tests

```bash
pip install -c constraints.txt -e ".[dev]"
pytest
```

### Dependency versions

Every package the project uses (direct and transitive, 46 in total) is pinned to an exact version in `constraints.txt`. Those are the versions the test suite and the real collection were verified against. CI (`tests.yml`, `collect.yml`) and the API `Dockerfile` install with `-c constraints.txt`, and the frontend image uses `npm ci`, so a new upstream release can no longer change the behaviour of a run on its own — this had already happened once (SQLAlchemy 2.1 switched the default PostgreSQL driver and broke the scheduled collection). `pyproject.toml` additionally carries guard-rail ranges, e.g. `sqlalchemy<2.1`.

Upgrading is a deliberate step:

```bash
python -m venv .venv-upgrade && . .venv-upgrade/bin/activate   # Scripts\activate on Windows
pip install -c constraints.txt -e ".[dev]"
pip install -U <package>                  # e.g. sqlalchemy (raise the upper bound in pyproject.toml first if needed)
pytest                                    # and run scripts/run_collection.py against a test database
pip freeze --exclude-editable             # copy the new versions into constraints.txt
```

Constraints were resolved on Python 3.13 and checked to be installable on Python 3.12 / Linux (what CI and Docker use).

## Data quality

The LLM can misread a page, so its output is checked before saving (`src/market_intel/verify.py`):

1. **Evidence quote required.** For each price, image limit, prompt limit, multi-shot flag, quality score and uptime, the LLM must copy the exact sentence that states it. No quote means the field stays empty.
2. **The quote must exist** in the collected text (whitespace, case and markdown noise are ignored).
3. **The number must be in the quote**, and the quote must be about the right thing (a "per 1000 tokens" price is never accepted as a per-second price).
4. **Plausible range** (e.g. price 0.001-5 USD/s, uptime 90-100%).
5. **Right target.** The extracted name must match the requested key (version numbers must be equal; "Sora 2 Pro" is not "Sora 2"), and the name must appear in the text.

A failed field is dropped, never guessed. The approved quote, source URL and collection date are stored in the `field_evidence` table and exposed as `evidence` in the API; the dashboard shows them.

What this does **not** guarantee: that the page itself is correct or current (prices change often, so check the collection date), or which pricing tier or resolution a quoted price refers to (for example, Seedance 2.0 is $0.3034/s at 720p and $0.682/s at 1080p on fal.ai).

## Known limitations

- **Search can hit the wrong target.** Automatic search occasionally returns a page about a different model or provider (e.g. Seedance 1.0 instead of 2.0). The identity check rejects such collections, but free-text notes are not fact-checked, so they still need a human read.
- **Most existing values are unverified.** Only values collected through the verified pipeline carry evidence; earlier data shows as "not verified" (`*`) until it is re-collected.
- **Some fields are empty by nature.**
  - `prompt_max_chars` is empty for Seedance 2.0/2.5: neither ByteDance nor fal.ai publishes it. The Kling 3.0 (3,072) and Wan 2.2 (800) limits come from the creators' own API docs and may differ on hosting platforms such as fal.ai.
  - `quality_score` exists only when a review states an overall score on the same rubric (missing for Sora 2, Seedance 2.5 and Wan 2.2).
  - Replicate has no uptime % because its status page only lists incident days.
  - `$/image` and latency are not collected.
- **`max_reference_images` is not uniform.** Most models count start/end frames (1-2); Seedance 2.5 counts reference-mode inputs (50). Do not compare them directly.
- **The Luma Ray 3.2 record mixes sources**: specs from the Ray 2 page with a Ray 3.2 review.
- **The ranking treats missing data as 0** for that criterion, which penalises models whose platform simply does not publish it.
- **Provider overhead/latency** are not collected.
- **Price history starts on 2026-09-22**, when the `field_history` table was introduced. Every value change `store.py` accepts from then on (a brand-new record's first known value, or a later verified update) gets an append-only row (`entity_type`, `entity_key`, `field`, `old_value`, `new_value`, `source_url`, `changed_at`); it is exposed at `/api/history` and charted in the "Price history" tab. The 8 rows that already existed in Postgres at that date got a one-time seed row each, copied from their (already-verified) `field_evidence` entry, so the chart has a real starting point instead of being empty — there is no earlier price data to backfill beyond that.
- **Price basis is not guaranteed uniform across models**: a quoted price can be for a different resolution/tier depending on which one the source page happened to lead with (e.g. Seedance 2.0's price is for 720p, Seedance 2.5's is for 480p).
- **No migrations tool**: adding a column to an existing table needs a manual `ALTER TABLE` (Alembic would be the next step). New tables are created automatically.
- **Not deployed as a live service**: the API and Postgres run locally (or wherever Docker Compose is pointed); only the read-only static snapshot is published, on a schedule (see Scheduled collection).
