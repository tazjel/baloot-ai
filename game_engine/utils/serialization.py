"""
Serialization utilities to prevent JSON serialization errors.
"""
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def ensure_serializable(obj: Any, context: str = "") -> Any:
    """
    Validate that an object is JSON-serializable.
    
    Args:
        obj: Object to validate
        context: Context string for error messages
        
    Returns:
        The object if serializable
        
    Raises:
        TypeError: If object is not JSON-serializable
    """
    try:
        json.dumps(obj)
        return obj
    except TypeError as e:
        error_msg = f"Object not JSON-serializable"
        if context:
            error_msg += f" in {context}"
        error_msg += f": {e}"
        logger.error(error_msg)
        logger.error(f"Problematic object type: {type(obj)}")
        raise TypeError(error_msg)


def serialize_card(card) -> Dict[str, Any]:
    """
    Serialize a Card object to a dict.
    
    Args:
        card: Card object or dict
        
    Returns:
        Dict representation of the card
    """
    if hasattr(card, 'to_dict'):
        return card.to_dict()
    elif isinstance(card, dict):
        return card
    else:
        raise TypeError(f"Cannot serialize card of type {type(card)}")


def serialize_state(state: Dict[str, Any], context: str = "") -> Dict[str, Any]:
    """
    Recursively serialize a state dictionary, converting Card objects to dicts.
    
    Args:
        state: State dictionary to serialize
        context: Context string for error messages
        
    Returns:
        Serialized state dictionary
    """
    serialized = {}
    
    for key, value in state.items():
        if value is None:
            serialized[key] = None
        elif hasattr(value, 'to_dict'):
            # Object with to_dict method (e.g., Card)
            serialized[key] = value.to_dict()
        elif isinstance(value, dict):
            # Nested dict - recurse
            serialized[key] = serialize_state(value, f"{context}.{key}" if context else key)
        elif isinstance(value, list):
            # List - serialize each item
            serialized[key] = [
                item.to_dict() if hasattr(item, 'to_dict') else item
                for item in value
            ]
        else:
            # Primitive type
            serialized[key] = value
    
    # Validate the result
    ensure_serializable(serialized, context or "state")
    return serialized
