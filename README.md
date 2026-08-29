# DuckDB on Railway

Deploy and host [DuckDB](https://duckdb.org) as a persistent HTTP query service on [Railway](https://railway.com). Run SQL over a REST API against a database file that survives redeploys.

## About

DuckDB is a high-performance, in-process analytical (OLAP) SQL database. This template wraps it in a small [FastAPI](https://fastapi.tiangolo.com) service that exposes a `/query` endpoint, with a persistent volume so your data lives across deployments.

- **HTTP API**: `POST /query` with `{"sql": "SELECT 1"}` (or `GET /query?sql=...`)
- **Persistent**: database stored at `/data/duckdb.db` on a Railway volume
- **Secure**: requests require a `DUCKDB_API_KEY` bearer token (auto-generated per deploy)
- **Safe by default**: read-only unless `DUCKDB_ALLOW_WRITE=true` is set

## Deploy to Railway

[![Deploy on Railway](https://railway.com/button.svg)]([https://railway.com/new](https://railway.com/new/template/duckdb-railway?referralCode=qVHjLS))

Or via CLI:

```bash
railway login
railway link
railway up
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `DUCKDB_API_KEY` | *(auto-generated)* | Bearer token required for `/query`. |
| `DATABASE_PATH` | `/data/duckdb.db` | Where the database file lives (must be under the volume mount). |
| `DUCKDB_ALLOW_WRITE` | `false` | Set to `true` to allow `INSERT`/`UPDATE`/`CREATE` etc. |
| `DUCKDB_QUERY_TIMEOUT_MS` | `30000` | Max query execution time. |

## Usage

```bash
curl -H "Authorization: Bearer $DUCKDB_API_KEY" \
  -X POST https://<your-app>.up.railway.app/query \
  -d '{"sql": "SELECT 42 AS answer"}'
```

```json
{
  "columns": ["answer"],
  "rows": [[42]],
  "row_count": 1,
  "elapsed_ms": 0.54
}
```

## Development

```bash
cd app
pip install -r requirements.txt
DATABASE_PATH=./data/dev.db DUCKDB_API_KEY=dev uvicorn main:app --reload
```

## Why host DuckDB on Railway?

Railway is a single platform to deploy and scale your infrastructure. This template gives you a managed, always-on HTTP endpoint for DuckDB without running a server yourself — plus a volume-backed database file, health checks, and automatic SSL on a Railway domain.
