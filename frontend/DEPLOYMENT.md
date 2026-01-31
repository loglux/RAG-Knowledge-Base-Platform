# Frontend Deployment Guide

## Development Setup

For local development, Vite dev server proxies API requests to the backend:

```bash
cd frontend
npm install
npm run dev
```

Access at `http://localhost:5174`

## Domain Deployment with Nginx Reverse Proxy

### Overview

The application runs on Vite dev server (port 5174) behind nginx reverse proxy with:
- Frontend served from `/`
- API proxied from `/api/` to backend
- HTTPS termination
- HMR (Hot Module Replacement) over WebSocket

### Configuration Files

#### 1. Frontend Environment (`.env.local`)

Create `frontend/.env.local` (gitignored):

```bash
# Allow requests from domain
VITE_ALLOWED_HOSTS=your-domain.com

# HMR configuration for nginx reverse proxy
VITE_HMR_HOST=your-domain.com
VITE_HMR_PROTOCOL=wss
VITE_HMR_CLIENT_PORT=443

# API configuration - use relative path for nginx proxy
VITE_API_BASE_URL=
VITE_API_PREFIX=/api/v1
```

#### 2. Development Environment (`.env.development.local`)

This file is for local development without domain:

```bash
# Use empty base URL to work through Vite proxy (local) or nginx (domain)
VITE_API_BASE_URL=
VITE_API_PREFIX=/api/v1
```

The Vite dev server proxy (in `vite.config.ts`) handles `/api/*` requests locally.

#### 3. Nginx Configuration

Example nginx config on router/proxy server:

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://your-domain.com$request_uri;
}

# HTTPS reverse proxy
server {
    listen 443 ssl;
    server_name your-domain.com;

    # SSL certificates (adjust paths to your certificates)
    ssl_certificate     /path/to/fullchain.cer;
    ssl_certificate_key /path/to/private.key;

    # API -> backend (preserves /api prefix)
    location /api/ {
        proxy_pass http://<BACKEND_HOST>:<BACKEND_PORT>/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_connect_timeout 300;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Frontend + Vite HMR
    location / {
        proxy_pass http://<FRONTEND_HOST>:<FRONTEND_PORT>;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket / HMR support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_buffering off;
        proxy_connect_timeout 300;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

**Note:** Replace placeholders:
- `<BACKEND_HOST>` - Backend server IP/hostname
- `<BACKEND_PORT>` - Backend port (default: 8004)
- `<FRONTEND_HOST>` - Frontend server IP/hostname
- `<FRONTEND_PORT>` - Frontend port (default: 5174)

### How It Works

1. **Client Request**: Browser requests `https://your-domain.com`
2. **Nginx → Vite**: Nginx proxies to Vite dev server
3. **API Requests**: Frontend makes requests to `/api/v1/...` (relative path)
4. **Nginx → Backend**: Nginx proxies `/api/*` to backend
5. **HMR**: WebSocket connections upgrade for hot reload at `wss://your-domain.com`

### Starting Services

```bash
# Backend (on server)
cd /path/to/knowledge-base-platform
uvicorn app.main:app --host 0.0.0.0 --port 8004

# Frontend (on server)
cd /path/to/knowledge-base-platform/frontend
npm run dev  # Runs on port 5174

# Nginx (on router/proxy)
nginx -t && nginx -s reload
```

### Troubleshooting

#### Issue: "This host is not allowed"

Vite blocks requests from unrecognized hosts. Solution:
- Add domain to `VITE_ALLOWED_HOSTS` in `.env.local`
- Restart Vite dev server

#### Issue: API requests fail with CORS/SSL errors

Check:
1. `VITE_API_BASE_URL` is **empty** (not `http://...`)
2. Nginx config has `/api/` location with correct `proxy_pass`
3. Backend is running and accessible from nginx server

#### Issue: HMR not working

Check:
1. WebSocket upgrade headers in nginx config
2. `VITE_HMR_HOST` matches domain
3. `VITE_HMR_PROTOCOL=wss` for HTTPS
4. Browser console for WebSocket connection errors

### Production Build

For production deployment with static files:

```bash
cd frontend
npm run build

# Serve with nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    # API proxy (same as above)
    location /api/ {
        proxy_pass http://<BACKEND_HOST>:<BACKEND_PORT>/api/;
        # ... proxy headers
    }

    # Frontend static files
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Environment Variables Reference

| Variable | Description | Local Dev | Domain Deploy |
|----------|-------------|-----------|---------------|
| `VITE_API_BASE_URL` | API base URL | `` (empty) | `` (empty) |
| `VITE_API_PREFIX` | API path prefix | `/api/v1` | `/api/v1` |
| `VITE_ALLOWED_HOSTS` | Allowed hosts | - | `your-domain.com` |
| `VITE_HMR_HOST` | HMR WebSocket host | - | `your-domain.com` |
| `VITE_HMR_PROTOCOL` | HMR protocol | - | `wss` |
| `VITE_HMR_CLIENT_PORT` | HMR client port | - | `443` |

## File Structure

```
frontend/
├── .env.local              # Domain deployment config (gitignored)
├── .env.development.local  # Local development config (gitignored)
├── vite.config.ts         # Vite config with proxy & HMR
├── DEPLOYMENT.md          # This file (public)
└── DEPLOYMENT_LOCAL.md    # Local deployment with actual config (gitignored)
```

## Security Notes

- **Never commit** `.env.local` or `.env.development.local` to version control
- Keep `DEPLOYMENT_LOCAL.md` with actual server IPs/domains private
- Use strong SSL certificates for production
- Configure firewall rules to restrict access to backend ports
