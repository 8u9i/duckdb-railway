"""DuckDB HTTP query service for Railway.

Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import concurrent.futures
import os
import threading
import time

import duckdb
from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

app = FastAPI(title="DuckDB on Railway", version="1.0.0")

DATABASE_PATH = os.environ.get("DATABASE_PATH", "/data/duckdb.db")
API_KEY = os.environ.get("DUCKDB_API_KEY", "")
ALLOW_WRITE = os.environ.get("DUCKDB_ALLOW_WRITE", "").lower() in ("1", "true", "yes", "on")
QUERY_TIMEOUT_MS = int(os.environ.get("DUCKDB_QUERY_TIMEOUT_MS", "30000"))

_conn = None
_conn_lock = None


def _get_conn() -> duckdb.DuckDBPyConnection:
    """Open a persistent DuckDB connection (lazily, thread-safe)."""
    global _conn, _conn_lock
    if _conn is None:
        if _conn_lock is None:
            _conn_lock = __import__("threading").Lock()
        with _conn_lock:
            if _conn is None:
                os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
                # DuckDB cannot open a non-existent file read-only; create it
                # first (writable) if needed, then reopen in the desired mode.
                if not os.path.exists(DATABASE_PATH):
                    tmp = duckdb.connect(DATABASE_PATH)
                    tmp.close()
                _conn = duckdb.connect(DATABASE_PATH, read_only=not ALLOW_WRITE)
    return _conn


def _require_auth(authorization: str | None = Header(default=None)):
    """Require a valid API key when one is configured."""
    if not API_KEY:
        return
    if not authorization or authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


class QueryRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="SQL statement to execute")
    params: dict | list | None = Field(default=None, description="Optional query parameters")


def _is_read_only(sql: str) -> bool:
    """Heuristic: reject statements that write when write access is disabled."""
    head = sql.lstrip().lower()
    return head.startswith(("select", "with", "show", "describe", "pragma", "explain", "values", "from"))


@app.get("/")
def root():
    return {"service": "duckdb", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query(req: QueryRequest, _: None = Depends(_require_auth)):
    if not ALLOW_WRITE and not _is_read_only(req.sql):
        raise HTTPException(status_code=400, detail="Write queries are disabled (set DUCKDB_ALLOW_WRITE=true to enable)")

    start = time.monotonic()
    try:
        con = _get_conn()

        def _run():
            cur = con.execute(req.sql, req.params or [])
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() if cur.description else []
            return columns, rows

        # DuckDB connections are not thread-safe for concurrent use; run the
        # query in a worker thread and enforce a timeout. A single worker keeps
        # queries serialized, which is the correct model for one in-process DB.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            try:
                columns, rows = future.result(timeout=QUERY_TIMEOUT_MS / 1000)
            except concurrent.futures.TimeoutError:
                raise HTTPException(status_code=408, detail="Query timed out")

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "elapsed_ms": round((time.monotonic() - start) * 1000, 2),
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - surface query errors to the client
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/query")
def query_get(sql: str, _: None = Depends(_require_auth)):
    return query(QueryRequest(sql=sql))
