---
description: Verify the health of the development environment (Redis, Backend, Frontend).
---

1. Check Redis Connection
```powershell
python -c "import redis; r=redis.from_url('redis://localhost:6379/0'); print('Redis PING:', r.ping())"
```

2. Check Backend API (Port 3005)
```powershell
curl -I http://localhost:3005/
```

3. Check Frontend (Port 3000)
```powershell
curl -I http://localhost:3000/
```

4. Check Bot Agent Imports
```powershell
python -c "from bot_agent import bot_agent; print('Bot Agent Loaded Successfully')"
```
