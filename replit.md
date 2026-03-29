# Workspace

## Overview

pnpm workspace monorepo using TypeScript + Python. Features a React frontend and a Python Flask backend for BabyCare AI Assistant.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **Frontend**: React + Vite + Tailwind CSS
- **Backend**: Python 3.11 + Flask (SQLite database)
- **API proxy**: Express 5 (TypeScript) proxies `/api` routes to Flask
- **Database**: SQLite (`artifacts/flask-backend/babycare.db`)
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Structure

```text
artifacts-monorepo/
├── artifacts/
│   ├── api-server/         # Express API server (proxy to Flask)
│   ├── babycare/           # React + Vite frontend (BabyCare AI)
│   └── flask-backend/      # Python Flask backend (all AI/ML logic)
│       ├── app.py          # Main Flask app with all routes
│       ├── requirements.txt
│       └── babycare.db     # SQLite database
├── lib/
│   ├── api-spec/           # OpenAPI spec + Orval codegen config
│   ├── api-client-react/   # Generated React Query hooks
│   ├── api-zod/            # Generated Zod schemas from OpenAPI
│   └── db/                 # Drizzle ORM schema + DB connection
├── scripts/                # Utility scripts
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── tsconfig.json
└── package.json
```

## Services

| Service | Port | Path | Description |
|---------|------|------|-------------|
| `babycare: web` | 25932 | `/` | React frontend |
| `api-server: API Server` | 8080 | `/api` | TypeScript proxy → Flask |
| `babycare: flask-api` | 5050 | `/api` | Python Flask backend |

The TypeScript API server proxies all `/api/{analyze-cry,analyze-photo,diagnose,growth,reminder,emergency,community}` requests to Flask on port 5050. `/api/healthz` is served by the TypeScript server directly.

## BabyCare AI Features

1. **Cry Analyzer** - Real audio signal processing using librosa (pitch/MFCCs/energy). Classifies: hunger, colic, tired, discomfort, pain
2. **Photo Analysis** - Image color analysis using PIL/numpy for rash, stool, jaundice detection
3. **Smart Diagnosis** - Rule-based emergency detection + LLM-ready symptom analysis with severity scoring (green/yellow/orange/red)
4. **Growth Tracker** - WHO 2006 standards percentile calculations, historical charts with Recharts
5. **Smart Reminders** - CRUD reminders with SQLite, type categories (feeding/sleep/vaccine/etc.)
6. **Emergency Assistant** - Decision tree triage (call_911/urgent_er/see_doctor_today/monitor_at_home), CPR guide
7. **Mothers Community** - Categorized posts, likes, comments, content moderation with keyword flagging

## API Routes (Flask)

```
POST /api/analyze-cry          # Audio → cry classification
POST /api/analyze-photo        # Image → condition analysis
POST /api/diagnose             # Symptoms → medical advice
POST /api/growth/add           # Add growth record
GET  /api/growth/history       # Growth history
GET  /api/growth/percentile    # WHO percentile calculation
POST /api/reminder/create      # Create reminder
GET  /api/reminder/list        # List reminders
DELETE /api/reminder/<id>      # Delete reminder
PATCH /api/reminder/<id>       # Update (complete) reminder
POST /api/emergency/assess     # Emergency triage
GET  /api/emergency/hospitals  # Nearby hospitals
POST /api/community/post       # Create post
GET  /api/community/feed       # Get posts (filterable by category)
POST /api/community/like       # Like a post
POST /api/community/comment    # Add comment
GET  /api/community/comments/<id> # Get post comments
```

## Running in Development

All workflows start automatically. Flask backend runs at port 5050, React frontend at port 25932, and the Express proxy at 8080 serving everything at `/api`.

## Python Dependencies

Installed: flask, flask-cors, librosa, soundfile, scipy, scikit-learn, numpy, pillow, requests, apscheduler, gunicorn
