# FedRetina Backend

FastAPI backend for the Privacy-Preserving Federated Diabetic Retinopathy Grading System.

## Quick Start

```bash
# 1. Install Python 3.12 and uv
# See https://docs.astral.sh/uv/getting-started/installation/

# 2. Copy environment template
cp .env.example .env
# Edit .env with real values — see config.py for the full list

# 3. Install dependencies
uv sync

# 4. Run the dev server
uv run uvicorn fedretina.main:app --reload --host 0.0.0.0 --port 8000

# 5. Verify
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Development

```bash
# Run tests
uv run pytest

# Lint and format
uv run ruff check src tests
uv run ruff format src tests

# Type check
uv run mypy src
```

## Environment Variables

All configuration is validated at startup via `src/fedretina/config.py`.
See `.env.example` for the full list. The app **refuses to start** if any
required variable is missing or malformed — that is by design.

## Security Notes

- **Never commit `.env`.** It contains service-role keys, DB passwords, and
  encryption keys.
- **Never paste `.env` values into chat, email, or code review.**
- **Rotate credentials immediately** if they are ever exposed.
- The audit chain (`audit_logs`) is append-only — see the migration files in
  `supabase/migrations/` for the enforcement details.

## Directory Layout

```
backend/
├── src/fedretina/       # Application source
├── tests/               # Test suite
├── supabase/            # Schema migrations (owned by backend)
├── pyproject.toml       # Dependencies
├── Dockerfile           # Production container
└── docker-compose.yml   # Local dev stack
```