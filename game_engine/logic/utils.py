
# Legacy / Shared Utils
# NOTE: Project logic moved to game_engine/logic/rules/projects.py
# Kept here if other modules strictly rely on it, but should be deprecated.

from game_engine.logic.rules.projects import check_project_eligibility as scan_hand_for_projects
from game_engine.logic.rules.projects import compare_projects
from game_engine.logic.rules.projects import sort_hand
from game_engine.logic.rules.projects import is_kawesh_hand

# Re-export for compatibility
__all__ = ['scan_hand_for_projects', 'compare_projects', 'sort_hand', 'is_kawesh_hand']

