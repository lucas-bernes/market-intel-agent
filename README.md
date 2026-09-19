# Market Intelligence Agent

A pipeline and dashboard that compares image-to-video AI models (Kling 3.0 and its competitors) and the API providers that host them (fal.ai and alternatives), so cost, quality and limits can be seen side by side.

Web pages (pricing, docs, reviews) are collected with FireCrawl, an LLM (DeepSeek) turns the raw text into structured records, and the results are stored in Postgres, served by a FastAPI backend and shown in a React dashboard.

## What it does

- **Models**: price per second, reference-image limit, multi-shot support, review summary (`quality_notes`) and, when a review states one, a numeric `quality_score`.
- **API providers**: pricing structure, published uptime and stability notes.
- **Dashboard**: weighted ranking (weights adjustable live), comparison table, model detail, provider table.
- **Merge rules**: the same model can be fed by several sources. Facts (name, provider, price, specs, score) are first-write-wins so a later mismatched source cannot overwrite them; free-text fields (`quality_notes`, `notes`) accumulate.

## Architecture

```
FireCrawl (scrape / search)  ->  DeepSeek (structured extraction)  ->  Postgres
                                                                         |
                                            React dashboard  <-  FastAPI (/api/models, /api/providers)
```

| Path | Role |
|---|---|
| `src/market_intel/sources.py` | Fetch a URL or search the web via FireCrawl |
| `src/market_intel/extract.py` | LLM extraction with forced tool use, validated by Pydantic |
| `src/market_intel/schema.py` | Pydantic models (`ModelComparison`, `ProviderComparison`) |
| `src/market_intel/store.py` | Persistence and merge rules |
| `src/market_intel/db.py` | SQLAlchemy models and engine |
| `src/market_intel/api.py` | FastAPI app |
| `src/market_intel/run_pipeline.py` | CLI entry point for the collection pipeline |
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
# Scrape one page for a model
docker compose exec api python -m market_intel.run_pipeline url "https://fal.ai/models/fal-ai/veo3.1/image-to-video" veo-3.1

# Search the web for a review of a model
docker compose exec api python -m market_intel.run_pipeline quality '"Veo 3.1" Google DeepMind video generation review 2026' veo-3.1

# Search the web for an API provider
docker compose exec api python -m market_intel.run_pipeline provider '"Baseten.co" model inference platform pricing uptime' baseten
```

The last argument is a stable key that identifies the record, so several sources can be merged into the same model.

### Tests

```bash
pip install -e ".[dev]"
pytest
```

## Known limitations

- **Search can hit the wrong target.** Automatic search occasionally returns a page about a different model or provider (e.g. Seedance 1.0 instead of 2.0). Identity fields are protected against overwrite, but free-text notes from a wrong page still get appended, so results need a human check.
- **Some fields are empty by nature.** `prompt_window_tokens` is empty for every model (video platforms don't document it like text LLMs do); `quality_score` exists only when a review states an overall score; `$/image` and latency are not collected.
- **Price history and provider overhead/latency** are not collected. The dashboard's "Price history" tab shows illustrative data only and is labelled as such.
- **No scheduled refresh yet**: collection is run by hand.
- **No migrations tool**: adding a column needs a manual `ALTER TABLE` (Alembic would be the next step).
- **Not deployed**: it runs locally with Docker Compose.
