import { defineRailway, github, project, service, volume } from "railway/iac";

// DuckDB HTTP query service with a persistent volume.
// Data survives redeploys via the volume mounted at /data.
const duckdbData = volume("duckdb-data", {
  sizeMB: 512,
});

const duckdb = service("duckdb", {
  source: github("YOUR_GITHUB_USERNAME/duckdb-railway", { branch: "main" }),
  start: "uvicorn main:app --host 0.0.0.0 --port $PORT",
  healthcheck: "/health",
  volumeMounts: {
    "/data": duckdbData,
  },
  env: {
    PORT: "8080",
    DATABASE_PATH: "/data/duckdb.db",
    DUCKDB_API_KEY: "${{ secret(32) }}",
  },
});

export default defineRailway(() =>
  project("duckdb-railway", {
    resources: [duckdb, duckdbData],
  })
);
