# Technical Debt & Refactoring Registry

This document tracks known areas of code that require cleanup, optimization, or refactoring.

## Format
- **[Component]**: Description of the debt. (Severity: High/Medium/Low)

## Active Debt

### Backend
- **[Main Runner (`main.py`)]**: The server runner heavily relies on monkey-patching `py4web` and manual route binding. This is fragile. (Severity: High)
- **[Global State]**: `room_manager.py` active state is in-memory. A crash loses all active games. (Severity: Medium)
- **[Redis Dependency]**: The AI Worker is tightly coupled to Redis. If Redis dies, the Bot freezes. Need a fallback or circuit breaker. (Severity: Medium)
- **[Replay Serialization]**: `make_serializable` is a recursive manual sanitizer. It's prone to recursion errors and missed fields. Should move to Pydantic or Marshmallow schemas. (Severity: High)

### AI & Vision
- **[YOLO Dataset]**: Training data is biased towards "clean" images. Need more real-world, noisy, poor-lighting examples. (Severity: High)
- **[MCTS Performance]**: Pure Python MCTS is slow for deep searches. Consider compiling critical paths with Cython or Numba. (Severity: Low)

### Frontend
- **[CSS/Scaling]**: The `HandFan` calculation currently has some hardcoded magic numbers for overlaps that might break on extremely small mobile screens. (Severity: Medium)
- **[Types]**: Some `any` types linger in the legacy parts of the socket handling code. (Severity: Low)
