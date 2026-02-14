"""
Baloot Online Game Capture v3.2 — Clean & Simple

Uses a clean Playwright browser. Logs in via the website, then navigates
to the game. Non-invasive interceptor decodes binary WS without modifying
the game's behavior.

Usage:  python tools/capture_archive.py
"""

import json
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── Config (loaded from external file — never committed) ─────────
import importlib.util, os
_cfg_path = os.path.expanduser("~/Desktop/capture_config.py")
if os.path.exists(_cfg_path):
    _spec = importlib.util.spec_from_file_location("capture_config", _cfg_path)
    _cfg = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_cfg)
    LOGIN_URL = _cfg.LOGIN_URL
    GAME_URL  = _cfg.GAME_URL
    EMAIL     = _cfg.EMAIL
    PASSWORD  = _cfg.PASSWORD
else:
    LOGIN_URL = ""
    GAME_URL  = ""
    EMAIL     = ""
    PASSWORD  = ""
    print(f"⚠ Config not found at {_cfg_path} — credentials will be empty.")
OUTPUT_DIR = Path(__file__).parent.parent / "captures"

# ── Non-invasive WebSocket Interceptor ───────────────────────────
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
        const hex = Array.from(bytes.slice(0, 300))
            .map(b => b.toString(16).padStart(2, '0'))
            .join(' ');
        return '[hex:' + bytes.length + '] ' + hex + (bytes.length > 300 ? '...' : '');
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
        console.log('[CAPTURE-v3] WS Connected:', url, 'binaryType:', ws.binaryType);

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

    // XHR interceptor
    window.__xhr_messages = [];
    const origOpen = XMLHttpRequest.prototype.open;
    const origSendXHR = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this._capture_method = method;
        this._capture_url = url;
        return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function(body) {
        const self = this;
        this.addEventListener('load', function() {
            window.__xhr_messages.push({
                t: Date.now(), method: self._capture_method, url: self._capture_url,
                status: self.status,
                request: typeof body === 'string' ? body?.substring(0, 3000) : null,
                response: self.responseText?.substring(0, 5000)
            });
        });
        return origSendXHR.apply(this, arguments);
    };

    return 'v3_non_invasive_injected';
})();
"""


def collect_messages(page):
    try:
        raw_ws = page.evaluate("JSON.stringify(window.__ws_messages || [])")
        raw_xhr = page.evaluate("JSON.stringify(window.__xhr_messages || [])")
        ws_msgs = json.loads(raw_ws)
        xhr_msgs = json.loads(raw_xhr)
        page.evaluate("window.__ws_messages = []; window.__xhr_messages = [];")
        return ws_msgs, xhr_msgs
    except Exception as e:
        print(f"  [!] Error collecting: {e}")
        return [], []


def save_capture(all_ws, all_xhr, output_dir, label="live"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"game_capture_{label}_{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "captured_at": datetime.now().isoformat(),
            "label": label,
            "ws_messages": len(all_ws),
            "xhr_requests": len(all_xhr),
            "websocket_traffic": all_ws,
            "http_traffic": all_xhr
        }, f, indent=2, ensure_ascii=False)
    return output_file


def print_live_summary(all_ws, all_xhr):
    connects = [m for m in all_ws if m.get('type') == 'CONNECT']
    sends    = [m for m in all_ws if m.get('type') == 'SEND']
    recvs    = [m for m in all_ws if m.get('type') == 'RECV']
    closes   = [m for m in all_ws if m.get('type') == 'CLOSE']
    errors   = [m for m in all_ws if m.get('type') == 'ERROR']

    print(f"\n  {'─' * 50}")
    print(f"  WS: {len(connects)} conn, {len(sends)} sent, {len(recvs)} recv, {len(closes)} close, {len(errors)} err")
    print(f"  XHR: {len(all_xhr)} requests")

    hex_msgs = blobs = text_msgs = 0
    for m in recvs + sends:
        data = m.get('data', '')
        if isinstance(data, str):
            if data.startswith('[hex:'):
                hex_msgs += 1
            elif data.startswith('[decoding-blob:') or data.startswith('[blob'):
                blobs += 1
            else:
                text_msgs += 1

    print(f"  Text: {text_msgs} | Hex: {hex_msgs} | Blob-pending: {blobs}")

    signalr_methods = {}
    for m in recvs + sends:
        data = m.get('data', '')
        if isinstance(data, str) and '"target"' in data:
            try:
                for part in data.split('\x1e'):
                    part = part.strip()
                    if not part:
                        continue
                    parsed = json.loads(part)
                    target = parsed.get('target', '')
                    if target:
                        direction = '→' if m['type'] == 'RECV' else '←'
                        key = f"{direction} {target}"
                        signalr_methods[key] = signalr_methods.get(key, 0) + 1
            except:
                pass

    if signalr_methods:
        print(f"\n  SignalR Methods:")
        for method, count in sorted(signalr_methods.items(), key=lambda x: -x[1]):
            print(f"    {method}: {count}x")

    recent = [m for m in all_ws[-30:]
              if m.get('data', '') not in ('{"type":6}\x1e', '')
              and not str(m.get('data', '')).startswith('[hex:')]
    if recent:
        print(f"\n  Recent readable messages:")
        for m in recent[-5:]:
            data = str(m.get('data', ''))[:150]
            print(f"    [{m['type']}] {data}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_ws = []
    all_xhr = []

    with sync_playwright() as p:
        print("=" * 60)
        print("  BALOOT ONLINE GAME CAPTURE v3.2")
        print("  Non-Invasive Binary Decoder")
        print("=" * 60)

        # Launch a CLEAN browser (not Chrome profile — too heavy)
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)

        # Pre-inject interceptor so it catches ALL WebSocket connections
        context.add_init_script(WS_INTERCEPTOR_JS)

        page = context.new_page()

        # ── Step 1: Login via website ────────────────────────────
        print("\n[1/3] Logging in...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        time.sleep(2)

        try:
            page.fill('input[type="email"], #email, [name="email"], [placeholder*="بريد"]', EMAIL)
            page.fill('input[type="password"], #password, [name="password"]', PASSWORD)
            page.click('button[type="submit"], #login-button, .login-btn')
            page.wait_for_load_state("networkidle", timeout=15000)
            print("  ✓ Logged in!")
        except Exception as e:
            print(f"  ⚠ Auto-login failed: {e}")
            print("  → Please log in manually in the browser, then press ENTER here.")
            import msvcrt
            while True:
                if msvcrt.kbhit() and msvcrt.getwch() == '\r':
                    break
                time.sleep(0.3)

        # ── Step 2: Navigate to game ─────────────────────────────
        print("\n[2/3] Loading game page...")
        page.goto(GAME_URL, wait_until="domcontentloaded")
        time.sleep(3)

        # Also inject directly in case context.add_init_script missed it
        try:
            result = page.evaluate(WS_INTERCEPTOR_JS)
            print(f"  ✓ Interceptor: {result}")
        except:
            print("  ✓ Interceptor active")

        # ── Step 3: Wait & Play ──────────────────────────────────
        print("\n  ⏳ Waiting for game to load (15 seconds)...")
        time.sleep(15)

        # Quick check — did we capture anything already?
        ws_msgs, xhr_msgs = collect_messages(page)
        all_ws.extend(ws_msgs)
        all_xhr.extend(xhr_msgs)
        print(f"  📊 Initial capture: {len(ws_msgs)} WS, {len(xhr_msgs)} XHR")

        print("\n" + "=" * 60)
        print("  🎮 GO PLAY!")
        print("=" * 60)
        print("""
  Browser is open. Log in to the game (if needed) and play!
  The interceptor is watching — it won't interfere.

  ENTER = live status  |  q = save & exit
        """)

        import msvcrt
        autosave_count = 0
        last_save = time.time()

        while True:
            try:
                start = time.time()
                user_input = None
                while time.time() - start < 10:
                    if msvcrt.kbhit():
                        char = msvcrt.getwch()
                        if char == '\r':
                            user_input = ''
                            break
                        elif char.lower() == 'q':
                            user_input = 'q'
                            break
                    time.sleep(0.3)

                ws_msgs, xhr_msgs = collect_messages(page)
                all_ws.extend(ws_msgs)
                all_xhr.extend(xhr_msgs)

                if time.time() - last_save > 30 and (ws_msgs or xhr_msgs):
                    autosave_count += 1
                    save_capture(all_ws, all_xhr, OUTPUT_DIR, f"v3_autosave_{autosave_count}")
                    last_save = time.time()
                    print(f"  [Auto-saved #{autosave_count}] +{len(ws_msgs)} WS, +{len(xhr_msgs)} XHR | Total: {len(all_ws)} WS")

                if user_input == 'q':
                    break
                elif user_input == '':
                    print(f"\n  📊 {len(all_ws)} WS + {len(all_xhr)} XHR captured")
                    print_live_summary(all_ws, all_xhr)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"  [!] Error: {e}")
                time.sleep(5)

        ws_msgs, xhr_msgs = collect_messages(page)
        all_ws.extend(ws_msgs)
        all_xhr.extend(xhr_msgs)

        output_file = save_capture(all_ws, all_xhr, OUTPUT_DIR, "v3_final")
        print(f"\n{'=' * 60}")
        print(f"  ✅ CAPTURE COMPLETE (v3.2)")
        print(f"{'=' * 60}")
        print(f"  Saved to: {output_file}")
        print_live_summary(all_ws, all_xhr)
        browser.close()
        print("\n  Done!")


if __name__ == "__main__":
    main()
