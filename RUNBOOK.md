# Runbook (General)

This runbook documents **how to run the system** and **why it is done this way**.
Keep it practical: steps, context, and troubleshooting.

---

## 1) Architecture & Responsibility

**Backend** runs in Docker (API + DB + Qdrant + OpenSearch).  
**Frontend** runs locally with Vite (dev UX, instant HMR, no rebuilds).

Why this split:
- Backend dependencies are heavy and stable → containerized.
- Frontend iteration is frequent → local Vite is fastest.

---

## 2) Ports & URLs

We use **5174** for the UI because **5173 is already taken** on this host.  
We use **8004** for the API because **8000/8001** were already occupied here.  
These are local conventions only—ports can be changed if needed (including the API port). If you change them, update:
- `frontend/.env` (`VITE_API_BASE_URL`)
- backend `CORS_ORIGINS`
- any docs/scripts that mention the port

`<host>` = the machine where the backend runs (server IP or hostname).  

**Example URLs (local convention):**
- UI: `http://<host>:5174`
- API: `http://<host>:8004`
- Health: `http://<host>:8004/api/v1/health`
- OpenSearch: `http://<host>:9200`

---

## 3) Backend (Docker)

Start backend services (order matters: db/qdrant/opensearch first, then api):
```bash
docker compose -f docker-compose.dev.yml up -d db qdrant opensearch api
```

Why:
- DB/Qdrant/OpenSearch must be running before the API.
- Docker guarantees stable dependencies.

---

## 4) Frontend (Vite)

Start Vite dev server:
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5174
```

Why:
- Local HMR = instant changes.
- Host `0.0.0.0` allows access from another machine.

---

## 5) How URLs Are Formed

The frontend calls the API directly with a base URL, **not** via Vite proxy.
We set:
```
VITE_API_BASE_URL=http://<host>:8004
VITE_API_PREFIX=/api/v1
```

This ensures the browser requests hit the API on the server IP
and never try to call `localhost` on the client machine.

---

## 6) Environment Variables

### Backend `.env`
Important:
- `CORS_ORIGINS` must include the frontend origin:
  `http://<host>:5174`
- `OPENSEARCH_URL` should point to the OpenSearch container:
  `http://opensearch:9200`

### Frontend `frontend/.env`
```
VITE_API_BASE_URL=http://<host>:8004
VITE_API_PREFIX=/api/v1
```

---

## 7) CORS: Applying Changes

Changing `.env` does **not** update a running container.
You must recreate the API container:

```bash
docker compose -f docker-compose.dev.yml up -d --force-recreate api
```

Verify:
```bash
docker exec kb-platform-api printenv CORS_ORIGINS
```

---

## 8) Migrations

If you pull backend changes, run migrations inside the API container:
```bash
docker exec kb-platform-api alembic upgrade head
```

---

## 9) Verification Checklist

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
