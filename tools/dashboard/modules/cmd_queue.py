"""
Command Queue Engine — Redis-based autonomous command execution.

AI agents push commands to Redis, the dashboard auto-executes them.
Safety allowlist prevents destructive commands from running.

Usage (from any agent or script):
    import redis
    r = redis.Redis(decode_responses=True)
    r.lpush("cmd:queue", json.dumps({"cmd": "pytest tests/unit/", "tag": "unit-tests"}))
"""

import json
import time
import uuid
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ── Safety Configuration ─────────────────────────────────────────

# Commands matching ANY of these patterns are ALLOWED
ALLOW_PATTERNS = [
    r"^pytest\b",                      # All pytest invocations
    r"^python\s+(-m\s+)?pytest\b",     # python -m pytest
    r"^python\s+.*\.py\b",             # python scripts
    r"^python\s+-c\b",                 # python -c oneliners
    r"^flake8\b",                      # Linting
    r"^pylint\b",                      # Linting
    r"^mypy\b",                        # Type checking
    r"^git\s+(status|diff|log|branch|show|stash list)\b",  # Read-only git
    r"^git\s+stash\b",                 # Git stash (save/pop)
    r"^npm\s+(run|test|start)\b",      # npm scripts
    r"^npx\b",                         # npx commands
    r"^node\b",                        # Node scripts
    r"^streamlit\b",                   # Streamlit commands
    r"^pip\s+(list|show|freeze)\b",    # Read-only pip
    r"^pip\s+install\b",              # pip install (allowed)
    r"^docker\s+(ps|images|logs)\b",   # Read-only docker
    r"^powershell\s+-ExecutionPolicy\s+Bypass\s+-File\b",  # PS scripts
    r"^dir\b",                         # Windows dir
    r"^type\b",                        # Windows type (cat equivalent)
    r"^echo\b",                        # Echo
    r"^redis-cli\b",                   # Redis CLI
    r"^where\b",                       # Windows which
    r"^curl\b",                        # HTTP requests
]

# Commands matching ANY of these patterns are ALWAYS BLOCKED
BLOCK_PATTERNS = [
    r"rm\s+-rf\b",                     # Recursive force delete
    r"del\s+/[sS]\b",                 # Windows recursive delete
    r"rmdir\s+/[sS]\b",              # Windows recursive rmdir
    r"git\s+push\s+.*--force\b",       # Force push
    r"git\s+reset\s+--hard\b",        # Hard reset
    r"git\s+clean\s+-f\b",            # Force clean
    r"format\s+[a-zA-Z]:\b",          # Format drive
    r"taskkill\s+.*python\b",         # Kill python (dashboard suicide)
    r"shutdown\b",                     # System shutdown
    r"restart\b",                      # System restart
    r"\|\s*rm\b",                      # Piped delete
    r">\s*/dev/null\s+2>&1\s*&\b",    # Background + suppress (sneaky)
]

# ── Core Queue Functions ─────────────────────────────────────────

QUEUE_KEY = "cmd:queue"
RESULT_PREFIX = "cmd:result:"
HISTORY_KEY = "cmd:history"
MAX_HISTORY = 100
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])  # baloot-ai root


def is_command_safe(cmd: str) -> tuple[bool, str]:
    """Check if a command is safe to execute.
    
    Returns (is_safe, reason).
    """
    cmd_stripped = cmd.strip()
    
    # Check blocked patterns first (highest priority)
    for pattern in BLOCK_PATTERNS:
        if re.search(pattern, cmd_stripped, re.IGNORECASE):
            return False, f"Blocked by safety rule: {pattern}"
    
    # Check allow patterns
    for pattern in ALLOW_PATTERNS:
        if re.search(pattern, cmd_stripped, re.IGNORECASE):
            return True, "Matched allowlist"
    
    return False, "Command not in allowlist. Add to ALLOW_PATTERNS if safe."


def push_command(redis_client, cmd: str, tag: str = "", timeout: int = 120) -> str:
    """Push a command to the execution queue.
    
    Returns the command ID.
    """
    cmd_id = str(uuid.uuid4())[:8]
    payload = json.dumps({
        "id": cmd_id,
        "cmd": cmd,
        "tag": tag or cmd.split()[0],
        "timeout": timeout,
        "pushed_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
    })
    redis_client.lpush(QUEUE_KEY, payload)
    return cmd_id


def poll_and_execute(redis_client) -> dict | None:
    """Pop one command from the queue and execute it.
    
    Returns the result dict, or None if queue is empty.
    """
    raw = redis_client.rpop(QUEUE_KEY)
    if not raw:
        return None
    
    try:
        job = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in queue", "raw": raw}
    
    cmd = job.get("cmd", "")
    cmd_id = job.get("id", "unknown")
    timeout = job.get("timeout", 120)
    tag = job.get("tag", "")
    
    # Safety check
    is_safe, reason = is_command_safe(cmd)
    
    if not is_safe:
        result = {
            "id": cmd_id,
            "cmd": cmd,
            "tag": tag,
            "status": "blocked",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _store_result(redis_client, cmd_id, result)
        return result
    
    # Execute
    result = {
        "id": cmd_id,
        "cmd": cmd,
        "tag": tag,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            cwd=PROJECT_ROOT,
            timeout=timeout,
        )
        result["status"] = "success" if proc.returncode == 0 else "failed"
        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout[-5000:] if len(proc.stdout) > 5000 else proc.stdout
        result["stderr"] = proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr
        result["duration"] = round(
            (datetime.now(timezone.utc) - datetime.fromisoformat(result["started_at"])).total_seconds(), 2
        )
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["reason"] = f"Exceeded {timeout}s timeout"
    except Exception as e:
        result["status"] = "error"
        result["reason"] = str(e)
    
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    _store_result(redis_client, cmd_id, result)
    return result


def get_result(redis_client, cmd_id: str) -> dict | None:
    """Retrieve the result of a completed command."""
    raw = redis_client.get(f"{RESULT_PREFIX}{cmd_id}")
    if raw:
        return json.loads(raw)
    return None


def get_queue_size(redis_client) -> int:
    """Get the number of commands waiting in the queue."""
    try:
        return redis_client.llen(QUEUE_KEY)
    except Exception:
        return 0


def get_recent_history(redis_client, count: int = 20) -> list[dict]:
    """Get recent command execution history."""
    try:
        items = redis_client.lrange(HISTORY_KEY, 0, count - 1)
        return [json.loads(item) for item in items]
    except Exception:
        return []


def _store_result(redis_client, cmd_id: str, result: dict):
    """Store result and add to history."""
    payload = json.dumps(result)
    # Store individual result (expires after 1 hour)
    redis_client.set(f"{RESULT_PREFIX}{cmd_id}", payload, ex=3600)
    # Add to history (capped list)
    redis_client.lpush(HISTORY_KEY, payload)
    redis_client.ltrim(HISTORY_KEY, 0, MAX_HISTORY - 1)
