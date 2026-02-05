# Frontend Deployment Guide

## Docker Setup (Default)

The frontend runs as a production build served by nginx (see `Dockerfile.production`).

```bash
docker compose up -d --build frontend
```

Access at `http://localhost:5174`

The nginx container proxies `/api/` requests to the backend container, so the UI can call `/api/v1` without a separate base URL.

---

## Reverse Proxy (Optional)

If you put the stack behind an external reverse proxy (nginx/traefik), proxy all traffic to the frontend container. The frontend will handle `/api/` internally.

Example nginx config:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /path/to/fullchain.cer;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://<FRONTEND_HOST>:<FRONTEND_PORT>;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_connect_timeout 300;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

Defaults:
- `<FRONTEND_PORT>`: 5174

---

## Environment Variables (Optional)

If you need a custom API base URL (different domain/port), set these before building the frontend:

Create `frontend/.env.production.local` (gitignored):

```bash
VITE_API_BASE_URL=http://<host>:8004
VITE_API_PREFIX=/api/v1
```

Then rebuild:

```bash
docker compose up -d --build frontend
```

---

## Troubleshooting

### Frontend not loading
```bash
docker compose ps
curl http://localhost:5174/health
docker compose logs -f frontend
```

### API calls failing
```bash
curl http://localhost:8004/api/v1/health
```

If CORS errors appear, ensure `CORS_ORIGINS` in `.env` includes `http://localhost:5174` and recreate the API container:

```bash
docker compose up -d --force-recreate api
```

---

## Security Notes

- Do not commit `.env.production.local`
- Keep API ports firewalled if exposed publicly
