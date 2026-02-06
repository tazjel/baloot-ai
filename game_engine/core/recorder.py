import time
import json
import logging
from redis import Redis
from game_engine.core.state import GameState

logger = logging.getLogger(__name__)

class TimelineRecorder:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        
    def record_state(self, state: GameState, event_type: str = "TICK", details: str = ""):
        """
        Push a state snapshot to the timeline stream.
        """
        try:
            stream_key = f"game:{state.roomId}:timeline"
            
            # Serialize
            # Use json() helper from pydantic (or model_dump_json in v2)
            # v1: .json(), v2: .model_dump_json()
            # We assume v1 or compatible.
            if hasattr(state, 'model_dump_json'):
                state_json = state.model_dump_json()
            else:
                state_json = state.json()
                
            entry = {
                "timestamp": time.time(),
                "event": event_type,
                "details": details,
                "state": state_json
            }
            
            # Add to Stream (maxlen 1000 to prevent explosion)
            self.redis.xadd(stream_key, entry, maxlen=1000)
            
        except Exception as e:
            logger.error(f"Failed to record timeline: {e}")
            pass

    def get_history(self, room_id: str, count: int = 50):
        """Retrieve last N entries"""
        stream_key = f"game:{room_id}:timeline"
        try:
            # XREVRANGE key + - COUNT N
            entries = self.redis.xrevrange(stream_key, count=count)
        except Exception as e:
            logger.error(f"Redis XREVRANGE failed: {e}")
            return []
            
        result = []
        if not entries:
            return result

        for item in entries:
            try:
                # Unpack safely
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    continue
                    
                eid, data = item
                
                # Handle ID
                entry_id = eid
                if isinstance(eid, bytes):
                    entry_id = eid.decode()
                elif not isinstance(eid, str):
                    entry_id = str(eid)
                
                # Helper to get field
                def get_field(d, key_str):
                    if not isinstance(d, dict): return None
                    # Try str key first, then bytes
                    if key_str in d: return d[key_str]
                    if key_str.encode() in d: return d[key_str.encode()]
                    return None
                
                ts_val = get_field(data, 'timestamp')
                event_val = get_field(data, 'event')
                details_val = get_field(data, 'details')
                state_val = get_field(data, 'state')
                
                # Decode values if bytes
                def decode_val(v):
                    if isinstance(v, bytes): return v.decode()
                    if v is None: return ""
                    return str(v)
                
                event_str = decode_val(event_val)
                details_str = decode_val(details_val)
                state_str = decode_val(state_val)
                
                # Parse State JSON
                state_obj = {}
                if state_str:
                    try:
                        state_obj = json.loads(state_str)
                    except json.JSONDecodeError:
                        state_obj = {"error": "Invalid JSON", "raw": state_str}

                result.append({
                    "id": entry_id,
                    "timestamp": float(ts_val) if ts_val else 0.0,
                    "event": event_str,
                    "details": details_str,
                    "state": state_obj
                })
            except Exception as e:
                logger.error(f"Error parsing timeline entry: {e}")
                continue
                
        return result
