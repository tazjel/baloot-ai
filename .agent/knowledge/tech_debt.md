# Technical Debt & Refactoring Registry

This document tracks known areas of code that require cleanup, optimization, or refactoring.

## Format
- **[Component]**: Description of the debt. (Severity: High/Medium/Low)

## Active Debt

### Backend
- **[Bot Logic]**: The current bot implementation (`SimpleBot`) relies on basic heuristics. It should eventually be decoupled into a proper Strategy pattern or state machine to allow for "Smart" vs "Basic" bots. (Severity: Medium)
- **[Main Runner (`main.py`)]**: The server runner heavily relies on monkey-patching `py4web` and manual route binding. This is fragile. It should be refactored to use standard WSGI patterns or official `py4web` serving methods if possible. (Severity: High)
- **[Global State]**: `room_manager.py` still uses in-memory dictionaries for active games. While we added SQL persistence for *archived* matches, active state is lost on restart. (Severity: Medium)

### Frontend
- **[CSS/Scaling]**: The `HandFan` calculation currently has some hardcoded magic numbers for overlaps that might break on extremely small mobile screens. (Severity: Medium)
- **[Types]**: Some `any` types linger in the legacy parts of the socket handling code. (Severity: Low)
