"""
GBaloot Capturer — Playwright-based WebSocket interceptor for game capture.

Cloned from tools/capture_archive.py for standalone use.
Launches a browser, injects a WS interceptor, and records all traffic.
"""
import json
import time
from datetime import datetime
from pathlib import Path

# ── Non-invasive WebSocket Interceptor (JavaScript) ──────────────
WS_INTERCEPTOR_JS = r"""
(() => {
    if (window.__ws_interceptor_v3) return 'already_injected_v3';
    window.__ws_interceptor_v3 = true;
    window.__ws_messages = [];
    window.__ws_msg_count = 0;

    const decoder = new TextDecoder('utf-8', { fatal: false });

    function decodeArrayBuffer(buf) {
        const bytes = new Uint8Array(buf);
        const text = decoder.decode(bytes);
        let printable = 0;
        for (let i = 0; i < Math.min(text.length, 100); i++) {
            const c = text.charCodeAt(i);
            if ((c >= 0x20 && c <= 0x7e) || (c >= 0x600 && c <= 0x6ff) || c === 0x0a || c === 0x0d || c === 0x1e) {
                printable++;
            }
        }
        if (printable > Math.min(text.length, 100) * 0.5) {
            return text.substring(0, 5000);
        }
        const hex = Array.from(bytes.slice(0, 4096))
            .map(b => b.toString(16).padStart(2, '0'))
            .join(' ');
        return '[hex:' + bytes.length + '] ' + hex + (bytes.length > 4096 ? '...' : '');
    }

    function decodeBlobToBuffer(blob, callback) {
        const reader = new FileReader();
        reader.onload = function() {
            callback(decodeArrayBuffer(reader.result));
        };
        reader.onerror = function() {
            callback('[blob-error:' + blob.size + ']');
        };
        reader.readAsArrayBuffer(blob);
    }

    const OrigWS = window.WebSocket;
    window._OrigWebSocket = OrigWS;

    window.WebSocket = function(url, protocols) {
        const ws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);

        window.__ws_messages.push({ t: Date.now(), type: 'CONNECT', url: url });
        window.__ws_msg_count++;

        const origSend = ws.send.bind(ws);
        ws.send = function(data) {
            try {
                let decoded;
                if (typeof data === 'string') {
                    decoded = data.substring(0, 5000);
                } else if (data instanceof ArrayBuffer) {
                    decoded = decodeArrayBuffer(data);
                } else if (data instanceof Uint8Array) {
                    decoded = decodeArrayBuffer(data.buffer);
                } else {
                    decoded = '[unknown-send:' + (data.byteLength || data.length || data.size || 0) + ']';
                }
                window.__ws_messages.push({ t: Date.now(), type: 'SEND', data: decoded, size: data.byteLength || data.length || 0 });
                window.__ws_msg_count++;
            } catch(e) {
                window.__ws_messages.push({ t: Date.now(), type: 'SEND', data: '[capture-error]', error: e.message });
            }
            return origSend(data);
        };

        ws.addEventListener('message', function(e) {
            try {
                if (typeof e.data === 'string') {
                    window.__ws_messages.push({ t: Date.now(), type: 'RECV', data: e.data.substring(0, 5000), size: e.data.length });
                    window.__ws_msg_count++;
                } else if (e.data instanceof ArrayBuffer) {
                    const decoded = decodeArrayBuffer(e.data);
                    window.__ws_messages.push({ t: Date.now(), type: 'RECV', data: decoded, size: e.data.byteLength });
                    window.__ws_msg_count++;
                } else if (e.data instanceof Blob) {
                    const idx = window.__ws_messages.length;
                    window.__ws_messages.push({ t: Date.now(), type: 'RECV', data: '[decoding-blob:' + e.data.size + ']', size: e.data.size });
                    window.__ws_msg_count++;
                    decodeBlobToBuffer(e.data, function(decoded) {
                        if (idx < window.__ws_messages.length) {
                            window.__ws_messages[idx].data = decoded;
                        }
                    });
                } else {
                    window.__ws_messages.push({ t: Date.now(), type: 'RECV', data: '[unknown-type]', size: 0 });
                    window.__ws_msg_count++;
                }
            } catch(e2) {
                window.__ws_messages.push({ t: Date.now(), type: 'RECV', data: '[capture-error]', error: e2.message });
            }
        });

        ws.addEventListener('close', function(e) {
            window.__ws_messages.push({ t: Date.now(), type: 'CLOSE', code: e.code, reason: e.reason });
            window.__ws_msg_count++;
        });

        ws.addEventListener('error', function(e) {
            window.__ws_messages.push({ t: Date.now(), type: 'ERROR', data: 'WebSocket error' });
            window.__ws_msg_count++;
        });

        return ws;
    };
    window.WebSocket.CONNECTING = OrigWS.CONNECTING;
    window.WebSocket.OPEN = OrigWS.OPEN;
    window.WebSocket.CLOSING = OrigWS.CLOSING;
    window.WebSocket.CLOSED = OrigWS.CLOSED;
    window.WebSocket.prototype = OrigWS.prototype;

    return 'v3_non_invasive_injected';
})();
"""


def collect_messages(page):
    """Collect captured WS messages from the browser page."""
    try:
        raw_ws = page.evaluate("JSON.stringify(window.__ws_messages || [])")
        ws_msgs = json.loads(raw_ws)
        page.evaluate("window.__ws_messages = [];")
        return ws_msgs
    except Exception as e:
        print(f"  [!] Error collecting: {e}")
        return []


def save_capture(all_ws: list, output_dir: Path, label: str = "live") -> Path:
    """Save captured traffic to a JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"game_capture_{label}_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "captured_at": datetime.now().isoformat(),
            "label": label,
            "ws_messages": len(all_ws),
            "xhr_requests": 0,
            "websocket_traffic": all_ws,
            "http_traffic": [],
        }, f, indent=2, ensure_ascii=False)
    return output_file


class GameCapturer:
    """High-level capture manager for use from Streamlit UI."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_ws: list = []
        self.is_running = False
        self.start_time = 0.0

    @property
    def message_count(self) -> int:
        return len(self.all_ws)

    @property
    def duration_sec(self) -> float:
        if self.start_time <= 0:
            return 0.0
        return time.time() - self.start_time

    def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "messages": self.message_count,
            "duration": self.duration_sec,
        }

    def collect_from_page(self, page) -> int:
        """Collect new messages from the browser page."""
        msgs = collect_messages(page)
        self.all_ws.extend(msgs)
        return len(msgs)

    def save(self, label: str = "gbaloot") -> Path:
        """Save all collected messages to disk."""
        return save_capture(self.all_ws, self.output_dir, label)

    def reset(self):
        """Reset the capturer state."""
        self.all_ws = []
        self.is_running = False
        self.start_time = 0.0
