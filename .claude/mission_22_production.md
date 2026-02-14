# Mission 22: "The Stage" — Production-Ready Game Experience

## Goal
Final polish for public release: Arabic localization, performance optimization, PWA support, and deployment pipeline.

## Deliverables

### 22.1 Localization (`frontend/src/i18n/`)
- Arabic-first UI: All game text in Arabic by default (بلوت, صن, حكم, مشروع)
- Translation files: `ar.json` + `en.json` with React context for switching
- RTL layout: All components work in RTL (card fan, score sheet, modals)
- Language toggle in Settings, persists to localStorage

### 22.2 Performance & Loading
- Code splitting: Lazy-load heavy modals (MatchReview, Settings, Store, Tutorial)
- Asset preloading during splash screen
- Skeleton loading for game state
- Bundle analysis: Target < 200KB gzipped

### 22.3 PWA & Offline
- Service worker: Cache static assets for offline single-player
- Install prompt on mobile browsers
- Offline banner: "Offline Mode — Playing against bots"
- Manifest: App icon, theme color, display: standalone

### 22.4 Containerization & CI/CD
- Backend Dockerfile: Python 3.11-slim, multi-stage, non-root, health check
- Frontend Dockerfile: Node 20 build → nginx serve, gzip, SPA fallback
- Docker Compose: Redis + Backend + Frontend (+ optional Celery worker)
- GitHub Actions: Test → Lint → Build → Deploy on push/PR
- `.env.example` with all variables documented

## Key Constraint
- Arabic is default language; English is secondary
- PWA offline mode supports bot play only (no multiplayer offline)
- Docker images must work on both amd64 and arm64
