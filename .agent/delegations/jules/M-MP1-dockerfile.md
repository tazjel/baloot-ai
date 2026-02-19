# Jules Task: M-MP1 — Server Dockerfile + Deploy Config

## Session Config
```
repo: tazjel/baloot-ai
branch: main
autoApprove: true
autoCreatePR: true
title: [M-MP1] Server Dockerfile and deploy config
```

## Prompt (copy-paste into Jules)

Create a production-ready Dockerfile for the Python backend server and update the existing docker-compose.yml.

Create these files:

1. **`Dockerfile`** (project root) — Production container for the Python server:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
ENV BALOOT_ENV=production
EXPOSE 3005
CMD ["python", "-m", "server.main"]
```

2. **`server/.env.example`** — Environment variable template:
```
BALOOT_ENV=production
JWT_SECRET=change-this-to-a-real-secret
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=https://baloot-ai.com
MAX_ROOMS=500
BOT_DELAY_MS=1500
```

3. **Update `docker-compose.yml`** — Add a `server` service block. KEEP all existing services (redis, redis-ui) intact. Add this service:
```yaml
  server:
    build: .
    ports:
      - "3005:3005"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - BALOOT_ENV=production
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - baloot_net
```

4. **`.dockerignore`** (project root):
```
.git
.agent
.claude
mobile/
frontend/node_modules
__pycache__
*.pyc
.env
```

Rules:
- DO NOT modify server/main.py, server/application.py, or any existing Python files
- DO NOT modify server/settings.py
- The Dockerfile must use python:3.12-slim base image
- The docker-compose update must KEEP the existing redis and redis-ui services intact — only ADD the server service
- DO NOT delete or rename any existing files

When done, create a PR with your changes. Title: "[M-MP1] Server Dockerfile and deploy config"
