"""
Push a command to the Dashboard Command Queue.

Usage:
    python tools/dashboard/push_cmd.py "pytest tests/unit/ -v"
    python tools/dashboard/push_cmd.py "git status" --tag git
    python tools/dashboard/push_cmd.py "flake8 server/" --timeout 30

The dashboard will auto-execute the command and store results in Redis.
"""

import argparse
import json
import sys

try:
    import redis
except ImportError:
    print("ERROR: redis package not installed. Run: pip install redis")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Push command to Dashboard queue")
    parser.add_argument("command", help="The command to execute")
    parser.add_argument("--tag", default="", help="Label for the command (default: first word)")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds (default: 120)")
    parser.add_argument("--host", default="127.0.0.1", help="Redis host")
    parser.add_argument("--port", type=int, default=6379, help="Redis port")
    args = parser.parse_args()

    try:
        r = redis.Redis(host=args.host, port=args.port, db=0, decode_responses=True, socket_timeout=5)
        r.ping()
    except Exception as e:
        print(f"ERROR: Cannot connect to Redis at {args.host}:{args.port} — {e}")
        sys.exit(1)

    # Import safety check
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from modules.cmd_queue import is_command_safe, push_command

    is_safe, reason = is_command_safe(args.command)
    if not is_safe:
        print(f"BLOCKED: {reason}")
        print(f"Command: {args.command}")
        sys.exit(1)

    cmd_id = push_command(r, args.command, tag=args.tag, timeout=args.timeout)
    print(f"OK — Queued command [{cmd_id}]")
    print(f"  cmd: {args.command}")
    print(f"  tag: {args.tag or args.command.split()[0]}")
    print(f"  timeout: {args.timeout}s")
    print(f"  Dashboard will auto-execute on next poll cycle.")


if __name__ == "__main__":
    main()
