"""
Protocol Decoder — SFS2X binary parser for captured Baloot game WebSocket traffic.

Decodes the SmartFoxServer 2X binary format used by the game server's WebSocket
protocol.  The format uses typed, named fields with recursive nesting (SFSObject
/ SFSArray).

Frame layout:
  0x80  [body_size:2B BE]  [SFSObject body]          — normal message
  0xa0  [compressed_len:2B BE]  [zlib deflate stream] — compressed message

SFSObject body:
  type(1B=0x12) + field_count(2B BE) + fields*
  Each field: name_len(2B BE) + name(UTF-8) + type(1B) + value

Usage:
    python tools/game_decoder.py captures/game_capture_v3_final_20260214_232007.json
"""
import json
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── SFS2X Type Codes ────────────────────────────────────────────
TYPE_NULL             = 0x00
TYPE_BOOL             = 0x01
TYPE_BYTE             = 0x02  # 1 byte signed
TYPE_SHORT            = 0x03  # 2 bytes signed BE
TYPE_INT              = 0x04  # 4 bytes signed BE
TYPE_LONG             = 0x05  # 8 bytes signed BE
TYPE_FLOAT            = 0x06  # 4 bytes IEEE 754 BE
TYPE_DOUBLE           = 0x07  # 8 bytes IEEE 754 BE
TYPE_UTF_STRING       = 0x08  # 2B len + UTF-8 data
TYPE_BOOL_ARRAY       = 0x09  # 2B count + 1B* bools
TYPE_BYTE_ARRAY       = 0x0A  # 4B len + bytes
TYPE_SHORT_ARRAY      = 0x0B  # 2B count + 2B* shorts
TYPE_INT_ARRAY        = 0x0C  # 2B count + 4B* ints
TYPE_LONG_ARRAY       = 0x0D  # 2B count + 8B* longs
TYPE_FLOAT_ARRAY      = 0x0E  # 2B count + 4B* floats
TYPE_DOUBLE_ARRAY     = 0x0F  # 2B count + 8B* doubles
TYPE_UTF_STRING_ARRAY = 0x10  # 2B count + (2B len + data)* strings
TYPE_SFS_ARRAY        = 0x11  # 2B count + (type + value)* elements
TYPE_SFS_OBJECT       = 0x12  # 2B count + (2B name_len + name + type + value)* fields

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

# Known action names for classification
GAME_ACTIONS = {
    "a_bid", "a_card_played", "a_cards_eating", "a_accept_next_move",
    "a_back", "find_match", "game_loaded", "game_state", "game_stat",
    "switch_seat", "hokom", "pass", "chat", "sira",
    "a_draw", "a_new_game", "a_rematch", "a_leave", "a_kick",
    "a_emoji", "a_sticker", "a_player_joined", "a_player_left",
    "a_round_end", "a_hand_dealt", "a_score_update", "a_trick_end",
    "a_disconnect", "a_reconnect", "a_timeout",
}

# Short field name → readable name mapping
FIELD_NAME_MAP = {
    "c": "controller",
    "a": "action_id",
    "p": "params",
    "u": "user_id",
    "s": "score",
    "b": "bid",
    "t": "team",
    "r": "round",
    "d": "dealer",
    "h": "hand",
    "m": "message",
    "n": "name",
    "v": "value",
    "g": "game_id",
    "zn": "zone_name",
    "un": "username",
    "pw": "password",
    "cl": "client",
    "api": "api_version",
    "st": "state",
    "tr": "trick",
    "pl": "players",
    "sc": "scores",
    "cd": "cards",
    "tp": "type",
    "rn": "round_num",
    "tn": "turn",
    "tm": "team",
    "rad": "radius",
    "ogs": "origin_score",
    "rap": "rapid",
    "rav": "raw_value",
    "iv": "is_valid",
    "ad": "additional",
}

# Structural patterns: field signature → action name
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
    """
    Recursive decoder for the SmartFoxServer 2X binary WebSocket protocol.

    Binary messages start with 0x80 + 2-byte body size (BE), followed by
    the root SFSObject body.  Compressed messages start with 0xa0 + 2-byte
    compressed length + zlib deflate stream; after decompression the payload
    is a raw SFSObject body (type byte + fields).

    SFSObject: type(0x12) + field_count(2B) + fields
    Each field: name_len(2B) + name(UTF-8) + value_type(1B) + value
    """

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
            self.errors.append(
                f"Unknown type 0x{type_code:02x} at pos {self.pos}"
            )
            return f"<unknown_type_0x{type_code:02x}>"

    def _read_sfs_object(self) -> dict:
        """Read an SFSObject: field_count(2B) + named fields."""
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
        """Read an SFSArray: count(2B) + typed elements."""
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
        """Read a bool array: count(2B) + 1B* bools."""
        count = self._read_uint16_be()
        return [bool(b) for b in self._read_bytes(count)]

    def _read_byte_array(self) -> list:
        """Read a byte array: length(4B) + raw bytes."""
        length = self._read_int32_be()
        if length < 0 or length > 1_000_000:
            self.errors.append(f"Byte array length {length} invalid")
            return []
        return list(self._read_bytes(length))

    def _read_short_array(self) -> list:
        """Read a short array: count(2B) + 2B* shorts."""
        count = self._read_uint16_be()
        return [struct.unpack(">h", self._read_bytes(2))[0] for _ in range(count)]

    def _read_int_array(self) -> list:
        """Read an int array: count(2B) + 4B* ints."""
        count = self._read_uint16_be()
        return [struct.unpack(">i", self._read_bytes(4))[0] for _ in range(count)]

    def _read_long_array(self) -> list:
        """Read a long array: count(2B) + 8B* longs."""
        count = self._read_uint16_be()
        return [struct.unpack(">q", self._read_bytes(8))[0] for _ in range(count)]

    def _read_float_array(self) -> list:
        """Read a float array: count(2B) + 4B* floats."""
        count = self._read_uint16_be()
        return [struct.unpack(">f", self._read_bytes(4))[0] for _ in range(count)]

    def _read_double_array(self) -> list:
        """Read a double array: count(2B) + 8B* doubles."""
        count = self._read_uint16_be()
        return [struct.unpack(">d", self._read_bytes(8))[0] for _ in range(count)]

    def _read_string_array(self) -> list:
        """Read a UTF string array: count(2B) + (2B len + data)* strings."""
        count = self._read_uint16_be()
        items = []
        for _ in range(count):
            items.append(self._read_utf_string())
        return items

    def decode(self, raw_body: bool = False) -> dict:
        """
        Decode a full SFS2X binary message.

        Frame: 0x80 [body_size:2B] [root_type:1B] [body...]
        Compressed (0xa0) messages are pre-decompressed before reaching here.

        If raw_body=True, data is a raw SFS body (type byte + content),
        e.g. from decompressed 0xa0 messages.

        Returns dict with:
          - "fields": the decoded root SFSObject fields {name: value}
          - "errors": any non-fatal decode errors
          - "bytes_consumed" / "bytes_total"
        """
        result = {}

        if not raw_body:
            # Framed message: 0x80 + body_size(2B) + root type + body
            if self.remaining < 4:
                raise DecodeError(f"Message too short: {self.remaining} bytes")

            header = self._read_uint8()
            if header != 0x80:
                raise DecodeError(
                    f"Expected 0x80 header, got 0x{header:02x}"
                )
            # 2-byte body size (informational — we just parse to completion)
            _body_size = self._read_uint16_be()

        # Read root type byte — should be 0x12 (SFSObject)
        try:
            root_type = self._read_uint8()
            if root_type == TYPE_SFS_OBJECT:
                result = self._read_sfs_object()
            else:
                # Unexpected root type, try to read as whatever it is
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


def hex_to_bytes(hex_string: str) -> tuple[bytes, bool]:
    """Convert a space-separated hex string to bytes.

    Handles the `[hex:NNN] AA BB CC ...` format from capture files.
    Returns (bytes, is_truncated) tuple.
    """
    truncated = False

    # Strip the [hex:NNN] prefix if present
    if hex_string.startswith("[hex:"):
        idx = hex_string.index("]")
        hex_string = hex_string[idx + 2:]  # skip '] '

    # Handle truncation marker
    if hex_string.endswith("..."):
        hex_string = hex_string[:-3].rstrip()
        truncated = True

    # Remove spaces and convert
    clean = hex_string.replace(" ", "")
    return bytes.fromhex(clean), truncated


def decode_card(code: str) -> str:
    """Decode a 2-char card code like 'da' to '♦A'."""
    if len(code) < 2:
        return code
    suit_char = code[0].lower()
    rank_chars = code[1:].lower()
    suit = SUIT_MAP.get(suit_char, suit_char)
    rank = RANK_MAP.get(rank_chars, rank_chars.upper())
    return f"{suit}{rank}"


def try_decompress(data: bytes) -> tuple[bytes, bool]:
    """Try to decompress data if it starts with the 0xa0 marker.

    Format: a0 [2-byte compressed_length] [zlib stream]
    Returns (data, was_compressed).
    """
    if len(data) > 3 and data[0] == 0xA0:
        try:
            compressed = data[3:]
            return zlib.decompress(compressed), True
        except zlib.error:
            pass
    return data, False


def decode_message(hex_string: str) -> dict:
    """Decode a single binary WebSocket message from its hex representation."""
    raw, truncated = hex_to_bytes(hex_string)
    raw, was_compressed = try_decompress(raw)
    decoder = SFS2XDecoder(raw)
    # Decompressed (0xa0) messages are raw SFS body — no 0x80 frame header
    result = decoder.decode(raw_body=was_compressed)
    result["truncated"] = truncated
    return result


# ── GameDecoder (high-level) ─────────────────────────────────────

@dataclass
class GameEvent:
    """A single decoded game event."""
    timestamp: float
    direction: str        # "SEND" or "RECV"
    action: str           # classified action name
    fields: dict          # decoded SFS fields
    raw_size: int = 0
    decode_errors: list = field(default_factory=list)


class GameDecoder:
    """
    High-level decoder that processes a full capture file and extracts
    a structured game timeline.
    """

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
        """Load the capture JSON file."""
        with open(self.path, "r", encoding="utf-8") as f:
            self.capture = json.load(f)
        return self.capture

    def decode_all(self) -> list[GameEvent]:
        """Decode all WebSocket messages in the capture."""
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
                # Binary message
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

                    # Track action counts
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
                # JSON / SignalR message
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
        """Classify a decoded binary message by its action type.

        SFS2X messages typically have:
          c = controller ID (byte)
          a = action/command ID (short)
          p = params (SFSObject with the payload)

        Classification priority:
        1. Known SFS command IDs (c + a)
        2. Direct field name match against known actions
        3. Nested param field name/value match
        4. Structural pattern matching
        """
        params = fields.get("p", {})

        # 1. Check for known action strings in param keys
        if isinstance(params, dict):
            for key in params:
                if key in GAME_ACTIONS:
                    return key
            # Check nested SFSObjects in params
            for key, val in params.items():
                if isinstance(val, dict):
                    for sub_key in val:
                        if sub_key in GAME_ACTIONS:
                            return sub_key
                    for sub_key, sub_val in val.items():
                        if isinstance(sub_val, str) and sub_val in GAME_ACTIONS:
                            return sub_val

        # 2. Direct field name match at root
        for key in fields:
            if key in GAME_ACTIONS:
                return key

        # 3. Check string values for action names (root + params)
        for src in (fields, params if isinstance(params, dict) else {}):
            for key, val in src.items():
                if isinstance(val, str) and val in GAME_ACTIONS:
                    return val

        # 4. Structural pattern matching on params
        if isinstance(params, dict):
            all_keys = set(params.keys())
            for val in params.values():
                if isinstance(val, dict):
                    all_keys.update(val.keys())
            for pattern_keys, action_name in STRUCTURAL_PATTERNS:
                if pattern_keys.issubset(all_keys):
                    return action_name

        # 5. SFS command-based classification
        controller = fields.get("c")
        action_id = fields.get("a")
        if controller is not None and action_id is not None:
            return f"sfs_cmd:{controller}:{action_id}"

        # 6. Fallback: check serialized form
        try:
            field_str = json.dumps(fields, default=str)
            for action in GAME_ACTIONS:
                if action in field_str:
                    return action
        except Exception:
            pass

        return "unknown"

    def get_game_timeline(self) -> list[dict]:
        """Return a simplified timeline of game events."""
        timeline = []
        for ev in self.events:
            entry = {
                "t": ev.timestamp,
                "dir": ev.direction,
                "action": ev.action,
                "size": ev.raw_size,
            }
            # Add key fields for important actions
            if ev.action == "a_card_played":
                card = ev.fields.get("card", ev.fields.get("c", ""))
                if card:
                    entry["card"] = decode_card(str(card))
            elif ev.action == "a_bid":
                entry["bid"] = ev.fields.get("bid", ev.fields.get("b", ""))
            elif ev.action in ("signalr:ReceiveMessage", "signalr:SendMessage"):
                entry["target"] = ev.fields.get("target", "")

            timeline.append(entry)
        return timeline

    def summary(self) -> str:
        """Return a human-readable summary of the decoded capture."""
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f"  SFS2X PROTOCOL DECODER RESULTS")
        lines.append(f"{'=' * 60}")
        lines.append(f"  File: {self.path.name}")
        lines.append(f"  Captured: {self.capture.get('captured_at', 'N/A')}")
        lines.append(f"  Label:    {self.capture.get('label', 'N/A')}")
        lines.append(f"")
        lines.append(f"  Messages: {self.stats['total_messages']}")
        lines.append(f"  Binary:   {self.stats['binary_messages']}")
        lines.append(f"  JSON:     {self.stats['json_messages']}")
        lines.append(f"  Decoded:  {self.stats['decoded_ok']}")
        lines.append(f"  Errors:   {self.stats['decode_errors']}")
        lines.append(f"")
        lines.append(f"  Actions:")
        for action, count in sorted(
            self.stats["actions_found"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"    {action:30s}: {count}")

        # Timeline stats
        if self.events:
            t_start = self.events[0].timestamp
            t_end = self.events[-1].timestamp
            dur = (t_end - t_start) / 1000
            lines.append(f"")
            lines.append(f"  Duration: {dur:.0f}s ({dur / 60:.1f} min)")

        lines.append(f"{'=' * 60}")
        return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/game_decoder.py <capture_file.json> [--timeline] [--json]")
        sys.exit(1)

    path = sys.argv[1]
    show_timeline = "--timeline" in sys.argv
    show_json = "--json" in sys.argv

    decoder = GameDecoder(path)
    decoder.load()
    decoder.decode_all()

    if show_json:
        timeline = decoder.get_game_timeline()
        print(json.dumps(timeline, indent=2, ensure_ascii=False))
    elif show_timeline:
        timeline = decoder.get_game_timeline()
        for entry in timeline:
            t = entry["t"]
            d = entry["dir"]
            a = entry["action"]
            extra = ""
            if "card" in entry:
                extra = f" → {entry['card']}"
            elif "bid" in entry:
                extra = f" → {entry['bid']}"
            print(f"  [{d:7s}] {a:25s}{extra}")
    else:
        print(decoder.summary())

        # Show first 5 decoded binary messages as samples
        binary_events = [e for e in decoder.events if e.direction != "CONNECT"
                         and not e.action.startswith("signalr")]
        if binary_events:
            print(f"\n  SAMPLE DECODED MESSAGES (first 5):")
            print(f"  {'─' * 55}")
            for ev in binary_events[:5]:
                print(f"\n  [{ev.direction}] {ev.action} (size={ev.raw_size})")
                for k, v in list(ev.fields.items())[:8]:
                    val_str = str(v)
                    if len(val_str) > 80:
                        val_str = val_str[:77] + "..."
                    print(f"    {k}: {val_str}")


if __name__ == "__main__":
    main()
