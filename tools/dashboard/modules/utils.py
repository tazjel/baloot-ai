import streamlit as st
import redis
import subprocess
import os

def get_redis_client():
    try:
        # Add timeout to prevent UI freeze
        r = redis.Redis(
            host='127.0.0.1',  # Force IPv4
            port=6379, 
            db=0, 
            decode_responses=True, 
            socket_timeout=5.0  # Increased to 5s for Windows Docker latency
        )
        r.ping()
        return r
    except (redis.ConnectionError, redis.TimeoutError, Exception):
        return None

def run_command(command, cwd=None):
    """Run a shell command and return result."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            cwd=cwd
        )
        return result
    except Exception as e:
        return None

def read_last_lines(filepath, n=50):
    if not os.path.exists(filepath):
        return [f"File not found: {filepath}"]
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-n:]
    except Exception as e:
        return [f"Error reading file: {e}"]
