# Knowledge Base Platform - Frontend

React + TypeScript frontend for the Knowledge Base Platform with RAG capabilities.

## Status: ✅ Running

**Dev Server**: http://192.168.10.32:5174/
**Backend API**: http://localhost:8004
**API Docs**: http://localhost:8004/docs

## Quick Start

```bash
# Install dependencies (already done)
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 7.3
- **Styling**: Tailwind CSS 3.4
- **UI Components**: Headless UI + Heroicons
- **HTTP Client**: Axios
- **State**: React Hooks (useState, useEffect)

## Configuration

### Environment Variables

`.env` file:
```bash
VITE_API_BASE_URL=http://localhost:8004
VITE_API_PREFIX=/api/v1
```

### Vite Config

`vite.config.ts`:
- Port: 5174
- Host: 0.0.0.0 (network access enabled)
- API Proxy: `/api` → `http://localhost:8004`

### Tailwind Config

- **Files**: `tailwind.config.cjs`, `postcss.config.cjs`
- **Theme**: Dark mode by default
- **Colors**:
  - Primary: Blue tones (#0ea5e9)
  - Accent: Purple tones (#a855f7)

## Current Features

### Implemented ✅

1. **Layout**
   - Header with app title and health status
   - Dark theme with gradient background
   - Responsive container

2. **Health Check**
   - Automatic backend connection check
   - Real-time status display in header

3. **Knowledge Bases**
   - Fetch and display list from API
   - Card-based grid layout
   - Empty state with CTA button

4. **API Integration**
   - Axios configured with base URL
   - Environment variable support
   - Vite proxy for CORS handling

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── App.tsx         # Main app component (current implementation)
│   ├── main.tsx        # React entry point
│   └── index.css       # Tailwind imports + custom styles
├── .env                # Environment configuration
├── index.html          # HTML template
├── vite.config.ts      # Vite configuration
├── tailwind.config.cjs # Tailwind configuration
├── postcss.config.cjs  # PostCSS configuration
├── tsconfig.json       # TypeScript configuration
└── package.json        # Dependencies
```

## Next Steps

### Phase 1: Foundation (Next)

- [ ] Create proper component structure
- [ ] Add React Router for navigation
- [ ] Implement Layout component (Header, Sidebar, Main)
- [ ] Create Dashboard page component
- [ ] Build KB card component
- [ ] Add "Create KB" modal

### Phase 2: Documents

- [ ] Document upload component (drag & drop)
- [ ] Document list with status
- [ ] Processing status polling
- [ ] Delete & reprocess actions

### Phase 3: Chat Interface

- [ ] Chat component with message history
- [ ] Message bubbles (user/assistant)
- [ ] Query settings panel
- [ ] Sources display with highlighting
- [ ] Streaming responses (future)

### Phase 4: Polish

- [ ] Loading states & skeletons
- [ ] Error handling & toasts
- [ ] Responsive design (mobile)
- [ ] Accessibility (ARIA labels, keyboard nav)
- [ ] Dark/Light theme toggle (optional)

## Development Notes

### Hot Reload

Changes to source files are automatically reflected in the browser thanks to Vite's HMR (Hot Module Replacement).

### API Proxy

All requests to `/api/*` are automatically proxied to the backend at `http://localhost:8004`. This handles CORS in development.

### Tailwind CSS

Custom utility classes defined in `src/index.css`:
- `.btn-primary` - Primary button style
- `.btn-secondary` - Secondary button style
- `.card` - Card container style
- `.input` - Input field style

### Known Issues Fixed

1. ✅ Tailwind 4.x PostCSS plugin error → Downgraded to v3.4
2. ✅ ES module vs CommonJS config → Renamed to `.cjs` files
3. ✅ Port conflicts → Cleaned up zombie processes

## Testing

Currently testing manually via:
```bash
# Check frontend loads
curl http://localhost:5174/

# Check API proxy works
curl http://localhost:5174/api/

# Check backend health
curl http://localhost:8004/
```

**Future**: Add Jest + React Testing Library for unit/integration tests.

## Deployment

### Development

Current setup - local dev server with Docker backend:
```bash
# Terminal 1: Backend
docker-compose -f docker-compose.dev.yml up

# Terminal 2: Frontend
cd frontend && npm run dev
```

### Production (Future)

Build static files and serve with Nginx or include in Docker:
```bash
npm run build
# Output in dist/ directory
```

## Troubleshooting

### Port already in use

```bash
# Find process using port
lsof -ti:5174

# Kill process
kill -9 <PID>

# Or use alternative port
npm run dev -- --port 5175
```

### API connection fails

1. Check backend is running: `docker-compose ps`
2. Check CORS configuration in backend `.env`
3. Verify proxy in `vite.config.ts`

### Tailwind styles not working

1. Ensure config files are `.cjs` (not `.js`)
2. Check Tailwind version is 3.x (not 4.x)
3. Verify `index.css` imports in `main.tsx`

---

**Last Updated**: 2026-01-24 01:30
**Status**: Development Ready
**Port**: 5174 ✅
**Backend**: Connected ✅
**Errors**: None ✅
