# Technical Debt & Refactoring Registry

This document tracks known areas of code that require cleanup, optimization, or refactoring.

## Format
- **[Component]**: Description of the debt. (Severity: High/Medium/Low)

## Active Debt

### Backend
- **[Bot Logic]**: The current bot implementation (`SimpleBot`) relies on basic heuristics. It should eventually be decoupled into a proper Strategy pattern or state machine to allow for "Smart" vs "Basic" bots. (Severity: Medium)
- **[Global State]**: `room_manager.py` uses a simple dictionary. As the app scales, this might need a Redis backend or database for persistence. (Severity: Low)

### Frontend
- **[CSS/Scaling]**: The `HandFan` calculation currently has some hardcoded magic numbers for overlaps that might break on extremely small mobile screens. (Severity: Medium)
- **[Types]**: Some `any` types linger in the legacy parts of the socket handling code. (Severity: Low)
