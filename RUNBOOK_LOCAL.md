# Runbook (Local Dev)

Operational guide for this local NAS setup.

## Services

Backend (Docker):
```bash
docker compose -f docker-compose.dev.yml up -d db qdrant opensearch api
```

Frontend (Vite on host):
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5174
```

URLs:
- UI: `http://192.168.10.32:5174`
- API: `http://192.168.10.32:8004`
- Health: `http://192.168.10.32:8004/api/v1/health`
- OpenSearch: `http://192.168.10.32:9200`

## Environment

Backend `.env`:
- `CORS_ORIGINS` must include `http://192.168.10.32:5174`
- `OPENSEARCH_URL` should be `http://opensearch:9200`

Frontend `frontend/.env`:
```
VITE_API_BASE_URL=http://192.168.10.32:8004
VITE_API_PREFIX=/api/v1
```

## Apply CORS Changes

The API container does not pick up `.env` changes on restart.
Recreate the container:
```bash
docker compose -f docker-compose.dev.yml up -d --force-recreate api
```

Verify:
```bash
docker exec kb-platform-api printenv CORS_ORIGINS
```

## Migrations

```bash
docker exec kb-platform-api alembic upgrade head
```

## BM25 Notes

- Switch Retrieval mode to **Hybrid** to enable BM25.
- Reindex existing docs via **Reindex for BM25** in the KB page.
- Per‑document badges show **Embeddings** and **BM25** status.

## Common Tasks

Start all:
```bash
./scripts/dev.sh up
```

Restart API:
```bash
./scripts/dev.sh restart api
```

Recreate API (for env changes):
```bash
./scripts/dev.sh recreate api
```

Logs:
```bash
./scripts/dev.sh logs api
```
