# Outpost Base Station

Base station software for the Outpost field weather station. Receives sensor data, stores readings, computes statistics, generates AI weather reports, and serves the API for the dashboard.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:Outpost-AI-Weather/outpost-base.git
cd outpost-base
uv sync
cp .env.example .env   # then fill in your API keys
mkdir data
```

## Running

Start the API server:

```bash
uv run uvicorn outpost_base.api.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive API docs.

## Testing

```bash
uv run pytest
uv run ruff check
```

## Project structure

| Folder | Purpose |
|---|---|
| `src/outpost_base/decoder/` | Converts raw LoRa packets into JSON |
| `src/outpost_base/ingest/` | Validates and saves readings |
| `src/outpost_base/db/` | Database models |
| `src/outpost_base/stats/` | Stats engine |
| `src/outpost_base/reports/` | AI report generation and validation |
| `src/outpost_base/api/` | API endpoints |
| `scripts/` | Mock data and utility scripts |
| `tests/` | Tests |