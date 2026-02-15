"""
GBaloot Decoder — Self-contained SFS2X binary protocol decoder.

Cloned from tools/game_decoder.py for standalone use.
Decodes SmartFoxServer 2X WebSocket binary traffic.
"""
import json
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── SFS2X Type Codes ────────────────────────────────────────────
TYPE_NULL             = 0x00
TYPE_BOOL             = 0x01
TYPE_BYTE             = 0x02
TYPE_SHORT            = 0x03
TYPE_INT              = 0x04
TYPE_LONG             = 0x05
TYPE_FLOAT            = 0x06
TYPE_DOUBLE           = 0x07
TYPE_UTF_STRING       = 0x08
TYPE_BOOL_ARRAY       = 0x09
TYPE_BYTE_ARRAY       = 0x0A
TYPE_SHORT_ARRAY      = 0x0B
TYPE_INT_ARRAY        = 0x0C
TYPE_LONG_ARRAY       = 0x0D
TYPE_FLOAT_ARRAY      = 0x0E
TYPE_DOUBLE_ARRAY     = 0x0F
TYPE_UTF_STRING_ARRAY = 0x10
TYPE_SFS_ARRAY        = 0x11
TYPE_SFS_OBJECT       = 0x12

TYPE_NAMES = {
    TYPE_NULL:             "null",
    TYPE_BOOL:             "bool",
    TYPE_BYTE:             "byte",
    TYPE_SHORT:            "short",
    TYPE_INT:              "int",
    TYPE_LONG:             "long",
    TYPE_FLOAT:            "float",
    TYPE_DOUBLE:           "double",
    TYPE_UTF_STRING:       "string",
    TYPE_BOOL_ARRAY:       "bool[]",
    TYPE_BYTE_ARRAY:       "byte[]",
    TYPE_SHORT_ARRAY:      "short[]",
    TYPE_INT_ARRAY:        "int[]",
    TYPE_LONG_ARRAY:       "long[]",
    TYPE_FLOAT_ARRAY:      "float[]",
    TYPE_DOUBLE_ARRAY:     "double[]",
    TYPE_UTF_STRING_ARRAY: "string[]",
    TYPE_SFS_ARRAY:        "SFSArray",
    TYPE_SFS_OBJECT:       "SFSObject",
}

# ── Card Mapping ─────────────────────────────────────────────────
SUIT_MAP = {"d": "♦", "h": "♥", "c": "♣", "s": "♠"}
RANK_MAP = {
    "a": "A", "2": "2", "3": "3", "4": "4", "5": "5",
    "6": "6", "7": "7", "8": "8", "9": "9", "10": "10",
    "j": "J", "q": "Q", "k": "K",
}

# R5: Import from canonical event_types (single source of truth)
from gbaloot.core.event_types import ALL_GAME_ACTIONS as GAME_ACTIONS

# Short field name → readable name
FIELD_NAME_MAP = {
    "c": "controller", "a": "action_id", "p": "params",
    "u": "user_id", "s": "score", "b": "bid", "t": "team",
    "r": "round", "d": "dealer", "h": "hand", "m": "message",
    "n": "name", "v": "value", "g": "game_id",
}

# Structural patterns
STRUCTURAL_PATTERNS = [
    ({"c", "p"}, "card_or_play"),
    ({"s", "t"}, "score_update"),
    ({"pl", "sc"}, "game_state_update"),
    ({"b"}, "bid_event"),
    ({"h", "cd"}, "hand_dealt"),
    ({"m"}, "chat_message"),
    ({"tr", "cd"}, "trick_update"),
]


class DecodeError(Exception):
    """Raised when a binary message cannot be decoded."""
    pass


class SFS2XDecoder:
    """Recursive decoder for the SmartFoxServer 2X binary WebSocket protocol."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.errors: list[str] = []

    @property
    def remaining(self) -> int:
        return len(self.data) - self.pos

    def _read_bytes(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise DecodeError(
                f"Unexpected EOF: need {n} bytes at pos {self.pos}, "
                f"only {self.remaining} left"
            )
        chunk = self.data[self.pos : self.pos + n]
        self.pos += n
        return chunk

    def _read_uint8(self) -> int:
        return self._read_bytes(1)[0]

    def _read_int16_be(self) -> int:
        return struct.unpack(">h", self._read_bytes(2))[0]

    def _read_uint16_be(self) -> int:
        return struct.unpack(">H", self._read_bytes(2))[0]

    def _read_int32_be(self) -> int:
        return struct.unpack(">i", self._read_bytes(4))[0]

    def _read_int64_be(self) -> int:
        return struct.unpack(">q", self._read_bytes(8))[0]

    def _read_float_be(self) -> float:
        return struct.unpack(">f", self._read_bytes(4))[0]

    def _read_double_be(self) -> float:
        return struct.unpack(">d", self._read_bytes(8))[0]

    def _read_utf_string(self) -> str:
        """Read a UTF-8 string: 2-byte BE length prefix + data."""
        length = self._read_uint16_be()
        if length == 0:
            return ""
        if length > 100_000:
            self.errors.append(f"String length {length} too large at pos {self.pos}")
            return f"<string_too_long:{length}>"
        raw = self._read_bytes(length)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def _read_value(self, type_code: int) -> Any:
        """Read a value based on its SFS2X type code."""
        if type_code == TYPE_NULL:
            return None
        elif type_code == TYPE_BOOL:
            return bool(self._read_uint8())
        elif type_code == TYPE_BYTE:
            return self._read_uint8()
        elif type_code == TYPE_SHORT:
            return self._read_int16_be()
        elif type_code == TYPE_INT:
            return self._read_int32_be()
        elif type_code == TYPE_LONG:
            return self._read_int64_be()
        elif type_code == TYPE_FLOAT:
            return self._read_float_be()
        elif type_code == TYPE_DOUBLE:
            return self._read_double_be()
        elif type_code == TYPE_UTF_STRING:
            return self._read_utf_string()
        elif type_code == TYPE_BOOL_ARRAY:
            return self._read_bool_array()
        elif type_code == TYPE_BYTE_ARRAY:
            return self._read_byte_array()
        elif type_code == TYPE_SHORT_ARRAY:
            return self._read_short_array()
        elif type_code == TYPE_INT_ARRAY:
            return self._read_int_array()
        elif type_code == TYPE_LONG_ARRAY:
            return self._read_long_array()
        elif type_code == TYPE_FLOAT_ARRAY:
            return self._read_float_array()
        elif type_code == TYPE_DOUBLE_ARRAY:
            return self._read_double_array()
        elif type_code == TYPE_UTF_STRING_ARRAY:
            return self._read_string_array()
        elif type_code == TYPE_SFS_ARRAY:
            return self._read_sfs_array()
        elif type_code == TYPE_SFS_OBJECT:
            return self._read_sfs_object()
        else:
            self.errors.append(f"Unknown type 0x{type_code:02x} at pos {self.pos}")
            return f"<unknown_type_0x{type_code:02x}>"

    def _read_sfs_object(self) -> dict:
        count = self._read_uint16_be()
        if count > 10_000:
            self.errors.append(f"SFSObject field count {count} too large")
            return {}
        result = {}
        for _ in range(count):
            if self.remaining < 3:
                self.errors.append("Truncated SFSObject field")
                break
            try:
                name = self._read_utf_string()
                type_code = self._read_uint8()
                value = self._read_value(type_code)
                result[name] = value
            except DecodeError as e:
                self.errors.append(str(e))
                break
        return result

    def _read_sfs_array(self) -> list:
        count = self._read_uint16_be()
        if count > 50_000:
            self.errors.append(f"SFSArray count {count} too large")
            return []
        items = []
        for _ in range(count):
            if self.remaining < 1:
                self.errors.append("Truncated SFSArray element")
                break
            try:
                elem_type = self._read_uint8()
                items.append(self._read_value(elem_type))
            except DecodeError as e:
                self.errors.append(str(e))
                break
        return items

    def _read_bool_array(self) -> list:
        count = self._read_uint16_be()
        return [bool(b) for b in self._read_bytes(count)]

    def _read_byte_array(self) -> list:
        length = self._read_int32_be()
        if length < 0 or length > 1_000_000:
            self.errors.append(f"Byte array length {length} invalid")
            return []
        return list(self._read_bytes(length))

    def _read_short_array(self) -> list:
        count = self._read_uint16_be()
        return [struct.unpack(">h", self._read_bytes(2))[0] for _ in range(count)]

    def _read_int_array(self) -> list:
        count = self._read_uint16_be()
        return [struct.unpack(">i", self._read_bytes(4))[0] for _ in range(count)]

    def _read_long_array(self) -> list:
        count = self._read_uint16_be()
        return [struct.unpack(">q", self._read_bytes(8))[0] for _ in range(count)]

    def _read_float_array(self) -> list:
        count = self._read_uint16_be()
        return [struct.unpack(">f", self._read_bytes(4))[0] for _ in range(count)]

    def _read_double_array(self) -> list:
        count = self._read_uint16_be()
        return [struct.unpack(">d", self._read_bytes(8))[0] for _ in range(count)]

    def _read_string_array(self) -> list:
        count = self._read_uint16_be()
        return [self._read_utf_string() for _ in range(count)]

    def decode(self, raw_body: bool = False) -> dict:
        """Decode a full SFS2X binary message."""
        result = {}
        if not raw_body:
            if self.remaining < 4:
                raise DecodeError(f"Message too short: {self.remaining} bytes")
            header = self._read_uint8()
            if header != 0x80:
                raise DecodeError(f"Expected 0x80 header, got 0x{header:02x}")
            _body_size = self._read_uint16_be()

        try:
            root_type = self._read_uint8()
            if root_type == TYPE_SFS_OBJECT:
                result = self._read_sfs_object()
            else:
                self.errors.append(
                    f"Expected root SFSObject (0x12), got 0x{root_type:02x}"
                )
                value = self._read_value(root_type)
                result = {"_root": value}
        except DecodeError as e:
            self.errors.append(str(e))

        return {
            "fields": result,
            "errors": self.errors,
            "bytes_consumed": self.pos,
            "bytes_total": len(self.data),
        }


# ── Utility Functions ────────────────────────────────────────────

def hex_to_bytes(hex_string: str) -> tuple[bytes, bool]:
    """Convert '[hex:NNN] AA BB ...' to (bytes, is_truncated)."""
    truncated = False
    if hex_string.startswith("[hex:"):
        idx = hex_string.index("]")
        hex_string = hex_string[idx + 2:]
    if hex_string.endswith("..."):
        hex_string = hex_string[:-3].rstrip()
        truncated = True
    clean = hex_string.replace(" ", "")
    return bytes.fromhex(clean), truncated


def decode_card(code: str) -> str:
    """Decode card code like 'da' to '♦A'."""
    if len(code) < 2:
        return code
    suit = SUIT_MAP.get(code[0].lower(), code[0])
    rank = RANK_MAP.get(code[1:].lower(), code[1:].upper())
    return f"{suit}{rank}"


def try_decompress(data: bytes) -> tuple[bytes, bool]:
    """Decompress 0xa0-framed data if present."""
    if len(data) > 3 and data[0] == 0xA0:
        try:
            return zlib.decompress(data[3:]), True
        except zlib.error:
            pass
    return data, False


def decode_message(hex_string: str) -> dict:
    """Decode a single binary WebSocket message from hex representation."""
    raw, truncated = hex_to_bytes(hex_string)
    raw, was_compressed = try_decompress(raw)
    decoder = SFS2XDecoder(raw)
    result = decoder.decode(raw_body=was_compressed)
    result["truncated"] = truncated
    return result


# ── High-Level Game Decoder ──────────────────────────────────────

@dataclass
class GameEvent:
    """A single decoded game event."""
    timestamp: float
    direction: str
    action: str
    fields: dict
    raw_size: int = 0
    decode_errors: list = field(default_factory=list)


class GameDecoder:
    """Processes a full capture file into structured game events."""

    def __init__(self, capture_path: str | Path):
        self.path = Path(capture_path)
        self.capture: dict = {}
        self.events: list[GameEvent] = []
        self.stats = {
            "total_messages": 0,
            "binary_messages": 0,
            "json_messages": 0,
            "decoded_ok": 0,
            "decode_errors": 0,
            "actions_found": {},
        }

    def load(self) -> dict:
        with open(self.path, "r", encoding="utf-8") as f:
            self.capture = json.load(f)
        return self.capture

    def decode_all(self) -> list[GameEvent]:
        if not self.capture:
            self.load()

        ws = self.capture.get("websocket_traffic", [])
        self.stats["total_messages"] = len(ws)

        for msg in ws:
            data = str(msg.get("data", ""))
            direction = msg.get("type", "RECV")
            timestamp = float(msg.get("t", 0))
            size = int(msg.get("size", 0))

            if data.startswith("[hex:"):
                self.stats["binary_messages"] += 1
                try:
                    decoded = decode_message(data)
                    action = self._classify(decoded.get("fields", {}))
                    errors = decoded.get("errors", [])
                    if decoded.get("truncated"):
                        errors.append("hex_truncated")
                    event = GameEvent(
                        timestamp=timestamp,
                        direction=direction,
                        action=action,
                        fields=decoded.get("fields", {}),
                        raw_size=size,
                        decode_errors=errors,
                    )
                    self.events.append(event)
                    self.stats["decoded_ok"] += 1
                    self.stats["actions_found"][action] = (
                        self.stats["actions_found"].get(action, 0) + 1
                    )
                except (DecodeError, Exception) as e:
                    self.stats["decode_errors"] += 1
                    self.events.append(GameEvent(
                        timestamp=timestamp,
                        direction=direction,
                        action="<decode_error>",
                        fields={"error": str(e), "raw_preview": data[:100]},
                        raw_size=size,
                        decode_errors=[str(e)],
                    ))

            elif data.startswith("{"):
                self.stats["json_messages"] += 1
                try:
                    clean = data.rstrip("\x1e")
                    parsed = json.loads(clean)
                    action = "signalr"
                    if "target" in parsed:
                        action = f"signalr:{parsed['target']}"
                    event = GameEvent(
                        timestamp=timestamp,
                        direction=direction,
                        action=action,
                        fields=parsed,
                        raw_size=size,
                    )
                    self.events.append(event)
                    self.stats["actions_found"][action] = (
                        self.stats["actions_found"].get(action, 0) + 1
                    )
                except json.JSONDecodeError:
                    self.stats["decode_errors"] += 1

            elif msg.get("type") == "CONNECT":
                self.events.append(GameEvent(
                    timestamp=timestamp,
                    direction="CONNECT",
                    action="ws_connect",
                    fields={"url": data},
                    raw_size=0,
                ))

        return self.events

    def _classify(self, fields: dict) -> str:
        """Classify a decoded message by its action type."""
        params = fields.get("p", {})
        if isinstance(params, dict):
            for key in params:
                if key in GAME_ACTIONS:
                    return key
            for key, val in params.items():
                if isinstance(val, dict):
                    for sub_key in val:
                        if sub_key in GAME_ACTIONS:
                            return sub_key
        for key in fields:
            if key in GAME_ACTIONS:
                return key
        for src in (fields, params if isinstance(params, dict) else {}):
            for key, val in src.items():
                if isinstance(val, str) and val in GAME_ACTIONS:
                    return val
        if isinstance(params, dict):
            all_keys = set(params.keys())
            for val in params.values():
                if isinstance(val, dict):
                    all_keys.update(val.keys())
            for pattern_keys, action_name in STRUCTURAL_PATTERNS:
                if pattern_keys.issubset(all_keys):
                    return action_name
        controller = fields.get("c")
        action_id = fields.get("a")
        if controller is not None and action_id is not None:
            return f"sfs_cmd:{controller}:{action_id}"
        try:
            field_str = json.dumps(fields, default=str)
            for action in GAME_ACTIONS:
                if action in field_str:
                    return action
        except Exception:
            pass
        return "unknown"

    def get_game_timeline(self) -> list[dict]:
        timeline = []
        for ev in self.events:
            entry = {
                "t": ev.timestamp,
                "dir": ev.direction,
                "action": ev.action,
                "size": ev.raw_size,
            }
            if ev.action == "a_card_played":
                card = ev.fields.get("card", ev.fields.get("c", ""))
                if card:
                    entry["card"] = decode_card(str(card))
            elif ev.action == "a_bid":
                entry["bid"] = ev.fields.get("bid", ev.fields.get("b", ""))
            timeline.append(entry)
        return timeline

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "  SFS2X PROTOCOL DECODER RESULTS",
            "=" * 60,
            f"  File: {self.path.name}",
            f"  Captured: {self.capture.get('captured_at', 'N/A')}",
            f"  Label:    {self.capture.get('label', 'N/A')}",
            "",
            f"  Messages: {self.stats['total_messages']}",
            f"  Binary:   {self.stats['binary_messages']}",
            f"  JSON:     {self.stats['json_messages']}",
            f"  Decoded:  {self.stats['decoded_ok']}",
            f"  Errors:   {self.stats['decode_errors']}",
            "",
            "  Actions:",
        ]
        for action, count in sorted(
            self.stats["actions_found"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"    {action:30s}: {count}")
        if self.events:
            dur = (self.events[-1].timestamp - self.events[0].timestamp) / 1000
            lines.append("")
            lines.append(f"  Duration: {dur:.0f}s ({dur / 60:.1f} min)")
        lines.append("=" * 60)
        return "\n".join(lines)
