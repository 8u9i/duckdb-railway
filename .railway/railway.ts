import { defineRailway, github, preserve, project, service, volume } from "railway/iac";

// DuckDB HTTP query service with a persistent volume.
// Data survives redeploys via the volume mounted at /data.
const duckdbData = volume("duckdb-data", {
  region: "europe-west4-drams3a",
  sizeMB: 512,
});

const duckdb = service("duckdb", {
  source: github("8u9i/duckdb-railway", { branch: "main" }),
  start: "uvicorn main:app --host 0.0.0.0 --port 8080",
  healthcheck: "/health",
  volumeMounts: {
    "/data": duckdbData,
  },
  env: {
    PORT: "8080",
    DATABASE_PATH: "/data/duckdb.db",
    DUCKDB_API_KEY: preserve(),
  },
});

export default defineRailway(() =>
  project("duckdb-railway", {
    resources: [duckdb, duckdbData],
  })
);
