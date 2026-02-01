# Agent Skills Library

This directory contains the capabilities (Skills) available to the AI Agent.

## Structure

### 1. Core Project Skills
These are custom-built skills specific to the Baloot AI project logic.
- **bot_lab**: Tools to interview the bot and debug decision making.
- **game_debugger**: Log analysis tools for lag/crashes.
- **scout_automation**: Management of the nightly game simulation.
- **verify_rules**: Guide for verifying game logic changes.
- **design_system**: UI reference for the "Premium ExternalApp" aesthetic.

### 2. External Skills Library (`/external`)
This folder contains the **Antigravity Awesome Skills** library (v4.0.0).
It provides 600+ general-purpose skills for:
- Architecture (C4, ADRs)
- Security (Pentesting, Audits)
- DevOps (Docker, CI/CD)
- React/TypeScript Best Practices

> **Note**: The `external` folder is treated as a read-only library. Do not modify files inside it unless necessary for a specific override.

## Usage
To use a skill, simply ask the agent:
> "Use the **@bot_lab** skill to debug this hand."
> "Use the **@react-best-practices** skill (from external) to audit this component."
