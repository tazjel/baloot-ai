"""
SignalR Interceptor — Capture Kammelna game messages via WebSocket hooks.

Injects JavaScript into a Playwright page that monkey-patches the SignalR
HubConnection to intercept all server↔client messages. Messages are
buffered in `window.__signalr_capture` and collected by Python periodically.

Kammelna uses:
  - @microsoft/signalr v5.0.17
  - JsonHubProtocol over WebSockets
  - Unity WebGL (canvas rendering — no DOM game elements)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── JavaScript Hook (injected into the page) ─────────────────────

SIGNALR_HOOK_JS = r"""
(() => {
    // Guard: only inject once
    if (window.__signalr_interceptor_active) return 'already_injected';
    window.__signalr_interceptor_active = true;

    // ── Capture Buffer ──────────────────────────────────────────
    window.__signalr_capture = [];
    window.__signalr_meta = {
        hub_url: null,
        connected: false,
        methods_registered: [],
        connection_id: null,
        injected_at: new Date().toISOString(),
    };

    const MAX_BUFFER = 5000;  // Cap buffer size to prevent memory issues

    function pushMessage(direction, method, args) {
        const entry = {
            ts: new Date().toISOString(),
            dir: direction,  // "recv" or "send"
            method: method,
            args: args,
        };
        window.__signalr_capture.push(entry);
        // Trim old messages if buffer overflows
        if (window.__signalr_capture.length > MAX_BUFFER) {
            window.__signalr_capture = window.__signalr_capture.slice(-MAX_BUFFER);
        }
        // Also log to console for debugging
        console.log(
            `[SignalR Interceptor] ${direction.toUpperCase()} ${method}`,
            args
        );
    }

    // ── Hook WebSocket Constructor ──────────────────────────────
    // Captures the raw WS URL used by SignalR
    const OriginalWebSocket = window.WebSocket;
    window.WebSocket = function(url, protocols) {
        window.__signalr_meta.ws_url = url;
        console.log('[SignalR Interceptor] WebSocket opening:', url);

        const ws = protocols
            ? new OriginalWebSocket(url, protocols)
            : new OriginalWebSocket(url);

        // Listen for raw WS messages (fallback if SignalR hooks fail)
        ws.addEventListener('message', (event) => {
            try {
                // SignalR JSON protocol uses \x1e (record separator) as delimiter
                const raw = typeof event.data === 'string' ? event.data : '';
                const parts = raw.split('\x1e').filter(p => p.trim());
                for (const part of parts) {
                    const parsed = JSON.parse(part);
                    // SignalR message types: 1=Invocation, 2=StreamItem,
                    // 3=Completion, 6=Ping, 7=Close
                    if (parsed.type === 1 && parsed.target) {
                        // Only push if not already captured by the on() hook
                        // (avoid duplicates)
                        if (!window.__signalr_meta._on_hooked) {
                            pushMessage('recv', parsed.target, parsed.arguments || []);
                        }
                    }
                }
            } catch(e) {
                // Not all messages are JSON — ignore parse errors
            }
        });

        return ws;
    };
    // Copy static properties
    window.WebSocket.CONNECTING = OriginalWebSocket.CONNECTING;
    window.WebSocket.OPEN = OriginalWebSocket.OPEN;
    window.WebSocket.CLOSING = OriginalWebSocket.CLOSING;
    window.WebSocket.CLOSED = OriginalWebSocket.CLOSED;
    window.WebSocket.prototype = OriginalWebSocket.prototype;

    // ── Hook SignalR HubConnection ──────────────────────────────
    function hookSignalR() {
        if (!window.signalR || !window.signalR.HubConnection) {
            console.log('[SignalR Interceptor] signalR not loaded yet, will retry...');
            return false;
        }

        const HC = window.signalR.HubConnection.prototype;

        // Hook .start() — capture hub URL + connection state
        const origStart = HC.start;
        HC.start = function() {
            try {
                // Try different internal property patterns across signalR versions
                const conn = this.connection || this._connection || {};
                window.__signalr_meta.hub_url = conn.baseUrl || conn.url || conn._url || 'unknown';
                window.__signalr_meta.connected = true;
                console.log('[SignalR Interceptor] HubConnection.start()', window.__signalr_meta.hub_url);
                pushMessage('meta', 'connection_start', { url: window.__signalr_meta.hub_url });
            } catch(e) {
                console.warn('[SignalR Interceptor] Error reading connection info:', e);
            }
            return origStart.apply(this, arguments);
        };

        // Hook .on() — intercept incoming server messages
        const origOn = HC.on;
        HC.on = function(methodName, callback) {
            window.__signalr_meta.methods_registered.push(methodName);
            window.__signalr_meta._on_hooked = true;
            console.log('[SignalR Interceptor] Registered listener:', methodName);

            const wrappedCallback = function(...args) {
                pushMessage('recv', methodName, args);
                return callback.apply(this, args);
            };
            return origOn.call(this, methodName, wrappedCallback);
        };

        // Hook .send() — intercept outgoing fire-and-forget messages
        const origSend = HC.send;
        if (origSend) {
            HC.send = function(methodName, ...args) {
                pushMessage('send', methodName, args);
                return origSend.apply(this, [methodName, ...args]);
            };
        }

        // Hook .invoke() — intercept outgoing request-response messages
        const origInvoke = HC.invoke;
        if (origInvoke) {
            HC.invoke = function(methodName, ...args) {
                pushMessage('send', methodName, args);
                return origInvoke.apply(this, [methodName, ...args]);
            };
        }

        // Hook .stop() — track disconnection
        const origStop = HC.stop;
        HC.stop = function() {
            window.__signalr_meta.connected = false;
            pushMessage('meta', 'connection_stop', {});
            console.log('[SignalR Interceptor] HubConnection.stop()');
            return origStop.apply(this, arguments);
        };

        console.log('[SignalR Interceptor] All hooks installed successfully');
        return true;
    }

    // Try to hook immediately; retry if signalR not loaded yet
    if (!hookSignalR()) {
        let retries = 0;
        const interval = setInterval(() => {
            if (hookSignalR() || retries++ > 30) {
                clearInterval(interval);
            }
        }, 500);
    }

    return 'interceptor_injected';
})();
"""


# ── Python API ────────────────────────────────────────────────────

def inject_interceptor(page) -> dict:
    """Inject the SignalR interception hooks into a Playwright page.

    Call this BEFORE the page navigates to the game or immediately after
    page.goto() — the hooks must be in place before SignalR connects.

    Returns:
        dict with 'success' and injection status
    """
    try:
        result = page.evaluate(SIGNALR_HOOK_JS)
        logger.info("SignalR interceptor injected: %s", result)
        return {"success": True, "status": result}
    except Exception as e:
        logger.error("Failed to inject SignalR interceptor: %s", e)
        return {"success": False, "error": str(e)}


def collect_messages(page) -> list[dict]:
    """Collect and flush all buffered SignalR messages from the page.

    Reads `window.__signalr_capture`, returns the messages, and clears
    the browser-side buffer to prevent memory buildup.

    Returns:
        List of message dicts: { ts, dir, method, args }
    """
    try:
        messages = page.evaluate("""
            (() => {
                const msgs = window.__signalr_capture || [];
                window.__signalr_capture = [];
                return msgs;
            })()
        """)
        return messages or []
    except Exception as e:
        logger.error("Failed to collect SignalR messages: %s", e)
        return []


def get_connection_status(page) -> dict:
    """Get the current SignalR connection status.

    Returns:
        dict with hub_url, connected, methods_registered, ws_url, etc.
    """
    try:
        meta = page.evaluate("window.__signalr_meta || {}")
        return meta
    except Exception as e:
        logger.error("Failed to get connection status: %s", e)
        return {"connected": False, "error": str(e)}


def save_messages_to_file(messages: list[dict], filepath: str | Path) -> int:
    """Append messages to a JSONL file.

    Args:
        messages: List of message dicts to save
        filepath: Path to the .jsonl output file

    Returns:
        Number of messages written
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(filepath, "a", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            count += 1

    return count


def load_messages_from_file(filepath: str | Path) -> list[dict]:
    """Read messages from a JSONL file.

    Args:
        filepath: Path to the .jsonl file

    Returns:
        List of message dicts
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return []

    messages = []
    for line in filepath.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages
"""
Complexity: 7
Description: Core SignalR interceptor module with JS injection for hooking
HubConnection lifecycle (start/stop/on/send/invoke) and WebSocket constructor.
Captures all game messages to a browser buffer collected by Python.
"""
