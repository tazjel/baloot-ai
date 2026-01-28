from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PuzzleSolution:
    type: str  # "sequence", "goal_score", "win_trick"
    data: Any  # List of move strings, or target score, etc.

@dataclass
class Puzzle:
    id: str
    title: str
    description: str
    difficulty: str  # "Beginner", "Intermediate", "Advanced"
    initial_state_json: Dict[str, Any]
    solution: PuzzleSolution
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Puzzle':
        return cls(
            id=data.get('id', ''),
            title=data.get('title', 'Untitled'),
            description=data.get('description', ''),
            difficulty=data.get('difficulty', 'Beginner'),
            initial_state_json=data.get('initial_state', {}),
            solution=PuzzleSolution(
                type=data.get('solution', {}).get('type', 'sequence'),
                data=data.get('solution', {}).get('data', [])
            ),
            tags=data.get('tags', [])
        )
