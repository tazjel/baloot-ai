"""
GBaloot Data Models — shared types for sessions, events, and tasks.
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class GameEvent:
    """A single decoded game event."""
    timestamp: float
    direction: str          # "SEND", "RECV", "CONNECT"
    action: str             # classified action name
    fields: dict            # decoded SFS fields
    raw_size: int = 0
    decode_errors: list = field(default_factory=list)


@dataclass
class PlayerState:
    """State of a single player."""
    id: int = -1
    name: str = "Unknown"
    hand: list[str] = field(default_factory=list)
    position: str = "BOTTOM"  # TOP, BOTTOM, LEFT, RIGHT
    is_dealer: bool = False
    is_me: bool = False


@dataclass
class BoardState:
    """Full snapshot of the game board."""
    players: list[PlayerState] = field(default_factory=list)
    center_cards: list[str] = field(default_factory=list)
    current_player_id: int = -1
    phase: str = "WAITING"
    trump_suit: Optional[str] = None
    contract: Optional[str] = None
    scores: dict[str, int] = field(default_factory=lambda: {"US": 0, "THEM": 0})
    dealer_id: int = -1
    last_action: str = "None"
    event_index: int = 0

    def to_dict(self) -> dict:
        return asdict(self)



@dataclass
class CaptureSession:
    """Metadata for a raw capture file."""
    file_path: str
    captured_at: str = ""
    label: str = ""
    ws_count: int = 0
    xhr_count: int = 0
    duration_sec: float = 0.0
    tags: list = field(default_factory=list)
    notes: str = ""
    group: str = ""         # collection/group name

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_capture_file(cls, path: Path) -> "CaptureSession":
        """Create session metadata from a raw capture JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ws = data.get("websocket_traffic", [])
        duration = 0.0
        if ws and len(ws) > 1:
            t_start = ws[0].get("t", 0)
            t_end = ws[-1].get("t", 0)
            duration = (t_end - t_start) / 1000.0
        return cls(
            file_path=str(path),
            captured_at=data.get("captured_at", ""),
            label=data.get("label", ""),
            ws_count=data.get("ws_messages", len(ws)),
            xhr_count=data.get("xhr_requests", len(data.get("http_traffic", []))),
            duration_sec=duration,
        )


@dataclass
class ProcessedSession:
    """A fully decoded session with events and stats."""
    capture_path: str
    captured_at: str = ""
    label: str = ""
    stats: dict = field(default_factory=dict)
    events: list = field(default_factory=list)  # list of dicts (serialized GameEvent)
    timeline: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    notes: str = ""
    group: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, output_dir: Path) -> Path:
        """Save to a JSON file in the output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        name = Path(self.capture_path).stem
        out = output_dir / f"{name}_processed.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        return out

    @classmethod
    def load(cls, path: Path) -> "ProcessedSession":
        """Load from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)


@dataclass
class GameTask:
    """An action item generated from review insights."""
    id: str = ""
    title: str = ""
    description: str = ""
    status: str = "todo"    # "todo", "in_progress", "done"
    source_session: str = ""  # linked session path
    source_event_idx: int = -1
    created_at: str = ""
    updated_at: str = ""
    priority: str = "medium"  # "low", "medium", "high"

    def to_dict(self) -> dict:
        return asdict(self)


class TaskStore:
    """Simple JSON-based task persistence."""

    def __init__(self, tasks_dir: Path):
        self.tasks_dir = tasks_dir
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.tasks_dir / "tasks.json"

    def load_all(self) -> list[GameTask]:
        if not self.tasks_file.exists():
            return []
        with open(self.tasks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [GameTask(**t) for t in data]

    def save_all(self, tasks: list[GameTask]):
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in tasks], f, indent=2, ensure_ascii=False)

    def add(self, task: GameTask) -> GameTask:
        tasks = self.load_all()
        if not task.id:
            task.id = f"task_{len(tasks)+1:04d}"
        if not task.created_at:
            task.created_at = datetime.now().isoformat()
        task.updated_at = datetime.now().isoformat()
        tasks.append(task)
        self.save_all(tasks)
        return task

    def update(self, task_id: str, **kwargs) -> Optional[GameTask]:
        tasks = self.load_all()
        for t in tasks:
            if t.id == task_id:
                for k, v in kwargs.items():
                    if hasattr(t, k):
                        setattr(t, k, v)
                t.updated_at = datetime.now().isoformat()
                self.save_all(tasks)
                return t
        return None

    def delete(self, task_id: str) -> bool:
        tasks = self.load_all()
        new_tasks = [t for t in tasks if t.id != task_id]
        if len(new_tasks) < len(tasks):
            self.save_all(new_tasks)
            return True
        return False
