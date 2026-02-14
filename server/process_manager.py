import time
import os
import psutil
import logging
from redis import Redis

logger = logging.getLogger(__name__)

class Heartbeat:
    def __init__(self, service_name: str, redis_client: Redis, ttl: int = 10):
        self.service_name = service_name
        self.redis = redis_client
        self.ttl = ttl
        self.pid = os.getpid()
        self.key = f"heartbeat:{service_name}:{self.pid}"
        
    def beat(self, status: str = "running"):
        """Send a heartbeat to Redis"""
        try:
            self.redis.hset(self.key, mapping={
                "pid": self.pid,
                "status": status,
                "last_seen": time.time(),
                "cpu_percent": psutil.Process(self.pid).cpu_percent()
            })
            self.redis.expire(self.key, self.ttl)
        except Exception as e:
            # Don't crash on heartbeat failure, but log it
            logger.debug(f"Heartbeat beat failed: {e}")

    def stop(self):
        """Clean up on exit"""
        try:
            self.redis.delete(self.key)
        except Exception as e:
            logger.debug(f"Heartbeat stop cleanup failed: {e}")

class Reaper:
    """Utilities to find and kill zombies"""
    @staticmethod
    def get_active_workers(redis_client: Redis, service_name_pattern: str = "*") -> list:
        """Returns list of active worker data from heartbeats"""
        keys = redis_client.keys(f"heartbeat:{service_name_pattern}:*")
        workers = []
        for k in keys:
            data = redis_client.hgetall(k)
            if data:
                workers.append({
                    "key": k.decode(),
                    "pid": int(data.get(b'pid')),
                    "status": data.get(b'status').decode(),
                    "last_seen": float(data.get(b'last_seen'))
                })
        return workers

    @staticmethod
    def kill_zombies(redis_client: Redis):
        """
        Looks for processes that have NO heartbeat key but ARE running locally?
        Or logic: Logic must use the PID from the heartbeat.
        Actually, simplest 'Process Manager' is just checking if declared PIDs exist.
        """
        # Complex to implement safely in one go. 
        # For now, we just PROVIDE the heartbeat so the Dashboard can show "Offline/Online".
        pass
