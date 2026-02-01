
import json
import datetime
from enum import Enum
from typing import Any, Dict, List, Union
from pydantic import BaseModel

def serialize(obj: Any) -> Any:
    """
    Recursively attempts to serialize an object into a JSON-compatible format.
    
    Priority:
    1. None -> None
    2. Dict -> Dict (recursive)
    3. List/Tuple -> List (recursive)
    4. Has .to_dict() method -> call it (recursive)
    5. Enum -> .value
    6. datetime/date -> .isoformat()
    7. JSON primitives (str, int, float, bool) -> self
    8. Fallback -> str(obj)
    """
    if obj is None:
        return None
        
    # primitive types that are natively JSON serializable
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # Pydantic Model handling
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode='json', by_alias=True)

    # datetime handling
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()

    # Enum handling
    if isinstance(obj, Enum):
        return obj.value

    # Dictionary handling
    if isinstance(obj, dict):
        return {str(k): serialize(v) for k, v in obj.items()}

    # List/Tuple handling
    if isinstance(obj, (list, tuple)):
        return [serialize(v) for v in obj]

    # Custom Object with explicit serialization method
    if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
        try:
            return serialize(obj.to_dict())
        except Exception as e:
            # Fallback if to_dict crashes
            return f"<Serialization Error: {str(e)}>"
            
    # Try __dict__ if it exists and is not a protected type
    # (Be careful not to expose too much internal state)
    # For now, safe fallback is string representation
    
    return str(obj)
