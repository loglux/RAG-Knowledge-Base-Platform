# Runbook (General)

This runbook documents **how to run the system** and **why it is done this way**.
Keep it practical: steps, context, and troubleshooting.

---

## 1) Architecture & Responsibility

**Backend** runs in Docker (API + DB + Qdrant + OpenSearch).  
**Frontend** runs in Docker (nginx serving a production build).

---

## 2) Ports & URLs

We use **5174** for the UI because **5173 is already taken** on this host.  
We use **8004** for the API because **8000/8001** were already occupied here.  
These are local conventions only—ports can be changed if needed (including the API port). If you change them, update:
- `frontend/.env.production.local` (`VITE_API_BASE_URL`) and rebuild the frontend
- backend `CORS_ORIGINS`
- any docs/scripts that mention the port

`<host>` = the machine where the backend runs (server IP or hostname).  

**Example URLs (local convention):**
- UI: `http://<host>:5174`
- API: `http://<host>:8004`
- Health: `http://<host>:8004/api/v1/health`
- OpenSearch: `http://<host>:9200`

### Critical: Docker port binding for NAS + router nginx

For this deployment, service ports that must be reachable from LAN/router **must not** be bound to loopback.

- Correct: `0.0.0.0:PORT:PORT`
- Wrong for this setup: `127.0.0.1:PORT:PORT`

If `db/qdrant/opensearch` are bound to `127.0.0.1`, external reverse proxy paths can fail with `502 Bad Gateway` even when containers look healthy locally.

---

## 3) Stack (Docker)

Start the stack:
```bash
docker compose up -d --build
```

This brings up frontend, API, DB, and vector stores.

---

## 4) How URLs Are Formed

The frontend is served by nginx and proxies `/api/` to the API container,
so the UI can call `/api/v1` without a separate base URL.

---

## 5) Environment Variables

### Backend `.env`
Important:
- `CORS_ORIGINS` must include the frontend origin:
  `http://<host>:5174`
- `OPENSEARCH_URL` should point to the OpenSearch container:
  `http://opensearch:9200`

### Frontend env (optional)
If you need a custom API base URL (different domain/port), set:
```
VITE_API_BASE_URL=http://<host>:8004
VITE_API_PREFIX=/api/v1
```
Then rebuild the frontend image.

---

## 6) CORS: Applying Changes

Changing `.env` does **not** update a running container.
You must recreate the API container:

```bash
docker compose up -d --force-recreate api
```

Verify:
```bash
docker exec kb-platform-api printenv CORS_ORIGINS
```

---

## 7) Migrations

Migrations are run automatically on API container start (see `docker/entrypoint.sh`).
If the API is already running, you can apply migrations manually inside the container:
```bash
docker compose exec api alembic upgrade head
```

Note: Alembic revision IDs in this repo use numeric IDs (e.g., `012`, `013`). Ensure `revision` and `down_revision` follow this scheme to avoid resolution errors.

---

## 7.1) Update After `git pull` (Local Docker)

Recommended quick update:
```bash
git pull
docker compose down
docker compose up -d --build
```

Notes:
- Avoid deleting volumes unless you want to reset data.
- If builds are slow, you can skip cache pruning. Use `docker builder prune -f` only when needed.
- `docker-compose` (v1) is legacy; prefer `docker compose`.
- Ensure `./secrets/db_password` exists and matches the current DB password.

Example update script:
```bash
#!/bin/bash
set -e

echo ">>> Pulling latest changes..."
git pull

echo ">>> Stopping containers..."
docker compose down

echo ">>> Rebuilding and starting containers..."
docker compose up -d --build

echo ">>> Done!"
```

---

## 8) Verification Checklist

1) API health:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://<host>:8004/api/v1/health
```
Expect `200`.

2) Knowledge bases:
```bash
curl -s http://<host>:8004/api/v1/knowledge-bases/
```

3) Frontend reachable:
Open `http://<host>:5174`

4) MCP smoke test (via gateway):
- `tools/list`
- `list_knowledge_bases`
- `list_documents` for a known KB
- `rag_query` with a simple prompt

---

## 10) BM25 / Hybrid Notes

- Hybrid search requires OpenSearch to be reachable.
- Existing documents need **reprocessing** to populate BM25.
  Use the KB UI action: **Reindex for BM25**.
- Documents show per‑index status badges:
  **Embeddings** (Qdrant) and **BM25** (OpenSearch).

---

## 11) Common Errors

### CORS errors in browser
Cause:
- `CORS_ORIGINS` missing `http://<host>:5174`
- API container not recreated after `.env` change

Fix:
1) Update `.env`
2) Recreate API container

### Browser tries to hit `localhost:8004`
Cause:
- `VITE_API_BASE_URL` is unset or wrong
- Browser is using a stale bundle

Fix:
1) Set `VITE_API_BASE_URL` to server IP
2) Restart Vite
3) Hard refresh browser

### `502 Bad Gateway` on `<PUBLIC_DOMAIN>`
Cause:
- Router nginx cannot reach upstream on NAS
- Docker service published to loopback (`127.0.0.1`) instead of LAN (`0.0.0.0`)
- API healthcheck endpoint returns redirect and container never reaches `healthy`

Fix:
1) Verify published ports: `docker compose ps` (must show `0.0.0.0:...->...`)
2) Verify API health URL used by Docker healthcheck returns `200` directly (no `307`)
3) Recreate services: `docker compose up -d --build`
