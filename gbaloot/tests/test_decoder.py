"""
Tests for SFS2X binary protocol decoder (gbaloot.core.decoder).

Covers: type parsing (null/bool/int/string/arrays/objects), compressed messages,
action classification, hex conversion, truncated payloads, and edge cases.
"""
import json
import struct
import tempfile
import zlib
from pathlib import Path

import pytest

from gbaloot.core.decoder import (
    SFS2XDecoder,
    DecodeError,
    GameDecoder,
    GameEvent,
    decode_card,
    decode_message,
    hex_to_bytes,
    try_decompress,
    TYPE_NULL,
    TYPE_BOOL,
    TYPE_BYTE,
    TYPE_SHORT,
    TYPE_INT,
    TYPE_LONG,
    TYPE_FLOAT,
    TYPE_DOUBLE,
    TYPE_UTF_STRING,
    TYPE_SFS_OBJECT,
    TYPE_SFS_ARRAY,
    TYPE_INT_ARRAY,
    TYPE_BOOL_ARRAY,
    TYPE_UTF_STRING_ARRAY,
)


# ── Helpers ─────────────────────────────────────────────────────────

def _build_sfs_message(body: bytes) -> bytes:
    """Wrap body in SFS2X frame: 0x80 + body_size(2B BE) + body."""
    return b"\x80" + struct.pack(">H", len(body)) + body


def _sfs_object(*fields) -> bytes:
    """Build SFS2X Object bytes from (name, type_code, value_bytes) tuples.

    The object is prefixed with TYPE_SFS_OBJECT + field count.
    """
    header = struct.pack("B", TYPE_SFS_OBJECT)
    header += struct.pack(">H", len(fields))
    body = b""
    for name, tc, val_bytes in fields:
        name_bytes = name.encode("utf-8")
        body += struct.pack(">H", len(name_bytes)) + name_bytes
        body += struct.pack("B", tc) + val_bytes
    return header + body


def _utf_str(s: str) -> bytes:
    raw = s.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


# ── SFS2XDecoder Type Parsing ────────────────────────────────────────

class TestSFS2XDecoderTypes:
    """Test individual type code parsing."""

    def test_null_type(self):
        body = _sfs_object(("x", TYPE_NULL, b""))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["x"] is None

    def test_bool_true(self):
        body = _sfs_object(("flag", TYPE_BOOL, b"\x01"))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["flag"] is True

    def test_bool_false(self):
        body = _sfs_object(("flag", TYPE_BOOL, b"\x00"))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["flag"] is False

    def test_byte_type(self):
        body = _sfs_object(("b", TYPE_BYTE, b"\x2A"))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["b"] == 42

    def test_short_type(self):
        val = struct.pack(">h", -1234)
        body = _sfs_object(("s", TYPE_SHORT, val))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["s"] == -1234

    def test_int_type(self):
        val = struct.pack(">i", 100_000)
        body = _sfs_object(("n", TYPE_INT, val))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["n"] == 100_000

    def test_long_type(self):
        val = struct.pack(">q", 2**50)
        body = _sfs_object(("big", TYPE_LONG, val))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["big"] == 2**50

    def test_float_type(self):
        val = struct.pack(">f", 3.14)
        body = _sfs_object(("pi", TYPE_FLOAT, val))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert abs(result["fields"]["pi"] - 3.14) < 0.01

    def test_double_type(self):
        val = struct.pack(">d", 2.718281828)
        body = _sfs_object(("e", TYPE_DOUBLE, val))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert abs(result["fields"]["e"] - 2.718281828) < 1e-6

    def test_utf_string_type(self):
        text = "hello world"
        body = _sfs_object(("msg", TYPE_UTF_STRING, _utf_str(text)))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["msg"] == text

    def test_utf_string_empty(self):
        body = _sfs_object(("msg", TYPE_UTF_STRING, _utf_str("")))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["msg"] == ""

    def test_utf_string_arabic(self):
        text = "\u0628\u0644\u0648\u062a"  # "baloot" in Arabic
        body = _sfs_object(("name", TYPE_UTF_STRING, _utf_str(text)))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["name"] == text

    def test_int_array_type(self):
        count = struct.pack(">H", 3)
        vals = struct.pack(">iii", 10, 20, 30)
        body = _sfs_object(("arr", TYPE_INT_ARRAY, count + vals))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["arr"] == [10, 20, 30]


class TestSFS2XDecoderNested:
    """Test nested SFS objects and arrays."""

    def test_nested_sfs_object(self):
        # Inner object with one field
        inner = _sfs_object(("val", TYPE_INT, struct.pack(">i", 99)))
        # Outer object containing inner
        body = _sfs_object(("inner", TYPE_SFS_OBJECT, inner[1:]))  # skip the outer TYPE_SFS_OBJECT byte
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["inner"]["val"] == 99

    def test_sfs_array(self):
        # Build array: [42(int), "hi"(string)]
        array_body = struct.pack(">H", 2)  # count = 2
        array_body += struct.pack("B", TYPE_INT) + struct.pack(">i", 42)
        array_body += struct.pack("B", TYPE_UTF_STRING) + _utf_str("hi")
        body = _sfs_object(("list", TYPE_SFS_ARRAY, array_body))
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["list"] == [42, "hi"]

    def test_multiple_fields(self):
        body = _sfs_object(
            ("a", TYPE_INT, struct.pack(">i", 1)),
            ("b", TYPE_UTF_STRING, _utf_str("two")),
            ("c", TYPE_BOOL, b"\x01"),
        )
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert result["fields"]["a"] == 1
        assert result["fields"]["b"] == "two"
        assert result["fields"]["c"] is True


class TestSFS2XDecoderEdgeCases:
    """Edge cases and error handling."""

    def test_bad_header(self):
        dec = SFS2XDecoder(b"\xFF\x00\x00")
        with pytest.raises(DecodeError):
            dec.decode()

    def test_too_short_message(self):
        dec = SFS2XDecoder(b"\x80\x00")
        with pytest.raises(DecodeError):
            dec.decode()

    def test_unknown_type_code(self):
        # Type 0xFF does not exist
        body = struct.pack("B", TYPE_SFS_OBJECT)
        body += struct.pack(">H", 1)  # 1 field
        body += _utf_str("x")
        body += struct.pack("B", 0xFF)  # unknown type
        msg = _build_sfs_message(body)
        dec = SFS2XDecoder(msg)
        result = dec.decode()
        assert "x" in result["fields"]
        assert "<unknown_type_0xff>" in str(result["fields"]["x"])


# ── Hex Conversion ───────────────────────────────────────────────────

class TestHexConversion:

    def test_basic_hex(self):
        data, trunc = hex_to_bytes("AA BB CC")
        assert data == bytes([0xAA, 0xBB, 0xCC])
        assert trunc is False

    def test_hex_with_prefix(self):
        data, trunc = hex_to_bytes("[hex:3] AA BB CC")
        assert data == bytes([0xAA, 0xBB, 0xCC])
        assert trunc is False

    def test_hex_truncated(self):
        data, trunc = hex_to_bytes("[hex:100] AA BB CC...")
        assert data == bytes([0xAA, 0xBB, 0xCC])
        assert trunc is True


# ── Compression ──────────────────────────────────────────────────────

class TestCompression:

    def test_no_compression(self):
        data = b"\x80\x00\x05hello"
        result, compressed = try_decompress(data)
        assert result == data
        assert compressed is False

    def test_zlib_compression(self):
        payload = b"\x12\x00\x01" + _utf_str("test") + struct.pack("B", TYPE_NULL)
        compressed = zlib.compress(payload)
        framed = b"\xA0" + struct.pack(">H", len(compressed)) + compressed
        result, was_compressed = try_decompress(framed)
        assert was_compressed is True
        assert result == payload


# ── decode_card ──────────────────────────────────────────────────────

class TestDecodeCard:

    def test_hearts_ace(self):
        assert decode_card("ha") == "\u2665A"

    def test_spades_10(self):
        assert decode_card("s10") == "♠10"

    def test_diamond_jack(self):
        assert decode_card("dj") == "\u2666J"

    def test_short_code(self):
        assert decode_card("x") == "x"


# ── GameDecoder integration ──────────────────────────────────────────

class TestGameDecoder:

    def _write_capture_file(self, ws_traffic: list, tmp_path: Path) -> Path:
        """Write a minimal capture file and return its path."""
        capture = {
            "captured_at": "2024-01-01T00:00:00",
            "label": "test",
            "ws_messages": len(ws_traffic),
            "xhr_requests": 0,
            "websocket_traffic": ws_traffic,
            "http_traffic": [],
        }
        f = tmp_path / "test_capture.json"
        f.write_text(json.dumps(capture), encoding="utf-8")
        return f

    def test_load_and_decode_empty(self, tmp_path):
        f = self._write_capture_file([], tmp_path)
        decoder = GameDecoder(str(f))
        decoder.load()
        decoder.decode_all()
        assert decoder.stats["total_messages"] == 0
        assert len(decoder.events) == 0

    def test_json_message(self, tmp_path):
        ws = [{"t": 1000, "type": "RECV", "data": '{"target":"ping"}', "size": 20}]
        f = self._write_capture_file(ws, tmp_path)
        decoder = GameDecoder(str(f))
        decoder.load()
        decoder.decode_all()
        assert decoder.stats["json_messages"] == 1
        assert decoder.events[0].action == "signalr:ping"

    def test_connect_message(self, tmp_path):
        ws = [{"t": 1000, "type": "CONNECT", "data": "wss://example.com", "size": 0}]
        f = self._write_capture_file(ws, tmp_path)
        decoder = GameDecoder(str(f))
        decoder.load()
        decoder.decode_all()
        assert len(decoder.events) == 1
        assert decoder.events[0].action == "ws_connect"
        assert decoder.events[0].direction == "CONNECT"

    def test_binary_message_hex(self, tmp_path):
        # Build a valid SFS2X message
        inner = _sfs_object(("c", TYPE_INT, struct.pack(">i", 1)))
        msg_bytes = _build_sfs_message(inner)
        hex_str = "[hex:{}] ".format(len(msg_bytes))
        hex_str += " ".join(f"{b:02x}" for b in msg_bytes)

        ws = [{"t": 2000, "type": "RECV", "data": hex_str, "size": len(msg_bytes)}]
        f = self._write_capture_file(ws, tmp_path)
        decoder = GameDecoder(str(f))
        decoder.load()
        decoder.decode_all()
        assert decoder.stats["binary_messages"] == 1
        assert decoder.stats["decoded_ok"] == 1

    def test_classify_game_action(self, tmp_path):
        # Build an SFS2X message with p.game_state structure
        # game_state is in GAME_ACTIONS, so it should be classified
        inner_p = _sfs_object(("game_state", TYPE_NULL, b""))
        inner_body = inner_p[1:]  # strip the leading TYPE_SFS_OBJECT byte
        outer = _sfs_object(("p", TYPE_SFS_OBJECT, inner_body))
        msg_bytes = _build_sfs_message(outer)
        hex_str = "[hex:{}] ".format(len(msg_bytes))
        hex_str += " ".join(f"{b:02x}" for b in msg_bytes)

        ws = [{"t": 3000, "type": "RECV", "data": hex_str, "size": len(msg_bytes)}]
        f = self._write_capture_file(ws, tmp_path)
        decoder = GameDecoder(str(f))
        decoder.load()
        decoder.decode_all()
        assert decoder.events[0].action == "game_state"

    def test_get_game_timeline(self, tmp_path):
        ws = [{"t": 1000, "type": "CONNECT", "data": "wss://example.com", "size": 0}]
        f = self._write_capture_file(ws, tmp_path)
        decoder = GameDecoder(str(f))
        decoder.load()
        decoder.decode_all()
        timeline = decoder.get_game_timeline()
        assert len(timeline) == 1
        assert timeline[0]["action"] == "ws_connect"

    def test_summary_output(self, tmp_path):
        ws = [{"t": 1000, "type": "CONNECT", "data": "wss://example.com", "size": 0}]
        f = self._write_capture_file(ws, tmp_path)
        decoder = GameDecoder(str(f))
        decoder.load()
        decoder.decode_all()
        text = decoder.summary()
        assert "SFS2X PROTOCOL DECODER RESULTS" in text
        assert "test_capture" in text
