"""
GBoard Reconnaissance — JavaScript probes for discovering the game framework,
controller objects, card-play functions, and SFS2X client instance.

Architecture confirmed via live recon (Gemini):
  - Game Engine: Unity WebGL 3.5.1 (canvas rendering)
  - Networking: SFS2X 1.7.17 (SmartFoxServer binary over WSS)
  - Chat: Strophe XMPP (ejabberd, non-game)
  - Other: SignalR 5.0.17 (notifications, non-game)

The Unity instance is local-scoped (no window.unityInstance). Our primary
injection path is the SFS2X JS API — `SFS2X.Entities.Data.SFSObject` +
`SFS2X.Requests.System.ExtensionRequest` via the active SmartFox client.

Usage::

    from gbaloot.core.gboard_recon import run_full_recon, save_recon_report

    # With a Playwright page object:
    report = await run_full_recon(page)      # async
    report = run_full_recon_sync(page)       # sync
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Recon Scripts ────────────────────────────────────────────────────
# Each script is a self-contained JS IIFE that returns a JSON-serializable
# result. They are safe to run on any page (no side effects).

RECON_SCRIPTS: dict[str, str] = {

    # ── 1. Framework Identification ──────────────────────────────
    "framework": """() => {
        const r = {};
        // Game engines
        if (window.Phaser) r.phaser = Phaser.VERSION || '?';
        if (window.PIXI) r.pixi = PIXI.VERSION || '?';
        if (window.createjs) r.createjs = true;
        if (window.cc) r.cocos = true;
        if (window.Laya) r.laya = true;
        if (window.egret) r.egret = true;
        if (window.THREE) r.three = '?';
        if (window.BABYLON) r.babylon = true;
        // Unity WebGL
        if (window.unityFramework) r.unity = true;
        if (window.createUnityInstance) r.unity_create = true;
        // Networking
        if (window.SFS2X) r.sfs2x_api = true;
        if (window.SmartFox) r.smartfox = true;
        if (window.Strophe) r.strophe_xmpp = true;
        if (window.signalR || (window.microsoft && window.microsoft.signalR)) r.signalr = true;
        // Canvas
        r.canvas_count = document.querySelectorAll('canvas').length;
        r.iframes = document.querySelectorAll('iframe').length;
        return r;
    }""",

    # ── 2. SFS2X API Deep Inspection ─────────────────────────────
    # This is our PRIMARY injection vector
    "sfs2x_api": """() => {
        const result = { available: false };
        if (typeof SFS2X === 'undefined') return result;
        result.available = true;

        try {
            // Top-level namespace keys
            result.namespace_keys = Object.keys(SFS2X).slice(0, 20);

            // Requests namespace (for ExtensionRequest)
            if (SFS2X.Requests) {
                result.request_namespaces = Object.keys(SFS2X.Requests);
                if (SFS2X.Requests.System) {
                    result.system_requests = Object.keys(SFS2X.Requests.System);
                    // Check ExtensionRequest specifically
                    result.has_extension_request = typeof SFS2X.Requests.System.ExtensionRequest === 'function';
                }
            }

            // Data types (SFSObject, SFSArray)
            if (SFS2X.Entities) {
                result.entity_keys = Object.keys(SFS2X.Entities);
                if (SFS2X.Entities.Data) {
                    result.data_types = Object.keys(SFS2X.Entities.Data);
                    result.has_sfs_object = typeof SFS2X.Entities.Data.SFSObject === 'function';
                    result.has_sfs_array = typeof SFS2X.Entities.Data.SFSArray === 'function';
                }
            }

            // SmartFox constructor
            if (SFS2X.SmartFox) {
                result.has_smartfox_class = true;
                result.smartfox_proto = Object.getOwnPropertyNames(SFS2X.SmartFox.prototype)
                    .filter(k => typeof SFS2X.SmartFox.prototype[k] === 'function')
                    .slice(0, 30);
            }

            // SFS2X Events (for addEventListener)
            if (SFS2X.SFSEvent) {
                result.event_types = Object.keys(SFS2X.SFSEvent).slice(0, 30);
            }
        } catch(e) { result.error = e.message; }
        return result;
    }""",

    # ── 3. SFS2X Client Instance Finder ──────────────────────────
    # Scan window globals for the active SmartFox connection
    "sfs_client": """() => {
        const result = {};
        function find(obj, path, d) {
            if (d > 5 || !obj) return false;
            try {
                for (const k of Object.getOwnPropertyNames(obj)) {
                    try {
                        const v = obj[k]; const fp = path + '.' + k;
                        if (v && typeof v === 'object') {
                            // SmartFox instance signatures:
                            // 1. Has .send() + ._socketEngine (v1 API)
                            // 2. Has .send() + .sessionToken
                            // 3. Has .send() + .currentZone
                            // 4. Has .send() + .lastJoinedRoom
                            const hasSend = typeof v.send === 'function';
                            const hasSocket = v._socketEngine || v._ws || v._webSocket;
                            const hasSession = v.sessionToken || v.currentZone;
                            const hasRoom = v.lastJoinedRoom;

                            if (hasSend && (hasSocket || hasSession || hasRoom)) {
                                result.path = fp;
                                result.methods = Object.getOwnPropertyNames(v)
                                    .filter(m => typeof v[m] === 'function').slice(0, 40);
                                result.props = Object.getOwnPropertyNames(v)
                                    .filter(m => typeof v[m] !== 'function').slice(0, 40);
                                result.zone = v.currentZone || null;
                                result.sessionToken = v.sessionToken ? '[PRESENT]' : null;
                                try {
                                    result.room = v.lastJoinedRoom
                                        ? { name: v.lastJoinedRoom.name, id: v.lastJoinedRoom.id }
                                        : null;
                                } catch(e) {}
                                try {
                                    result.isConnected = v.isConnected ? v.isConnected() : null;
                                } catch(e) {}
                                return true;
                            }
                        }
                        if (d < 5 && v && typeof v === 'object' &&
                            !(v instanceof HTMLElement) &&
                            !(v instanceof Window) &&
                            !(v instanceof Document)) {
                            if (find(v, fp, d + 1)) return true;
                        }
                    } catch(e) {}
                }
            } catch(e) {}
            return false;
        }
        for (const k of Object.keys(window)) {
            try { if (find(window[k], k, 0)) break; } catch(e) {}
        }
        return result;
    }""",

    # ── 4. Unity Instance Probe ──────────────────────────────────
    # The Unity instance is local-scoped in Kammelna, but we might find
    # references via the canvas or framework globals
    "unity_probe": """() => {
        const result = {};
        // Check for Unity globals
        if (window.unityFramework) {
            result.unity_framework = typeof window.unityFramework;
            try {
                result.framework_keys = Object.keys(window.unityFramework).slice(0, 20);
            } catch(e) {}
        }
        if (window.createUnityInstance) {
            result.create_unity_instance = true;
        }
        // Check canvas for Unity markers
        const canvas = document.querySelector('#unity-canvas') || document.querySelector('canvas');
        if (canvas) {
            result.canvas_id = canvas.id;
            result.canvas_data = {};
            // Unity stores the instance on the canvas sometimes
            for (const k of Object.getOwnPropertyNames(canvas)) {
                if (k.startsWith('__') || k.startsWith('unity') || k.startsWith('Unity')) {
                    try {
                        const v = canvas[k];
                        result.canvas_data[k] = typeof v === 'function' ? '[function]' :
                            typeof v === 'object' ? '[object]' : v;
                    } catch(e) {}
                }
            }
        }
        // Check for Unity SendMessage (the bridge function)
        // In Unity WebGL, this is typically: unityInstance.SendMessage(gameObject, method, arg)
        // But if the instance isn't globally accessible, we need to find it
        result.send_message_global = typeof window.SendMessage === 'function';

        // Check for Unity modules (WASM exports)
        if (window.Module) {
            result.has_module = true;
            try {
                const keys = Object.keys(window.Module).slice(0, 20);
                result.module_keys = keys;
            } catch(e) {}
        }
        return result;
    }""",

    # ── 5. Global Game Objects ────────────────────────────────────
    "global_game_objects": """() => {
        const found = [];
        const skip = new Set([
            'chrome', '__coverage__', 'webkitStorageInfo', 'performance',
            'caches', 'cookieStore', 'scheduler', 'navigation', 'trustedTypes',
            'speechSynthesis', 'visualViewport', 'customElements',
            'SFS2X', 'Strophe', 'signalR', 'microsoft',
        ]);
        for (const key of Object.keys(window)) {
            if (skip.has(key) || key.startsWith('__')) continue;
            try {
                const val = window[key];
                if (val && typeof val === 'object' && val !== null &&
                    !(val instanceof HTMLElement) && !(val instanceof Window) &&
                    !(val instanceof Document)) {
                    const keys = Object.keys(val).slice(0, 20);
                    const funcs = keys.filter(k => typeof val[k] === 'function');
                    if (funcs.length > 2) {
                        found.push({ name: key, keys: keys, funcs: funcs });
                    }
                }
            } catch(e) {}
        }
        return found.slice(0, 30);
    }""",

    # ── 6. Card/Bid Function Scanner ─────────────────────────────
    "card_play_functions": """() => {
        const found = [];
        const pattern = /play|card|send|select|bid|trump|click|submit|deal/i;

        function scan(obj, path, depth) {
            if (depth > 3 || !obj) return;
            try {
                for (const key of Object.getOwnPropertyNames(obj)) {
                    try {
                        const val = obj[key];
                        const fp = path + '.' + key;
                        if (typeof val === 'function' && pattern.test(key)) {
                            found.push({
                                path: fp, name: key, args: val.length,
                                src: val.toString().substring(0, 300)
                            });
                        } else if (depth < 3 && val && typeof val === 'object' &&
                                   !(val instanceof HTMLElement) &&
                                   !(val instanceof Window) &&
                                   !(val instanceof Document)) {
                            scan(val, fp, depth + 1);
                        }
                    } catch(e) {}
                }
            } catch(e) {}
        }

        for (const key of Object.keys(window)) {
            try {
                const val = window[key];
                if (val && typeof val === 'object') scan(val, key, 0);
            } catch(e) {}
            if (found.length > 50) break;
        }
        return found;
    }""",

    # ── 7. WebSocket Connection Status ───────────────────────────
    "websocket_status": """() => {
        const result = {};
        const msgs = window.__ws_messages || [];
        result.interceptor_v4 = !!window.__ws_interceptor_v4;
        result.existing_hook_v2 = !!window.__ws_existing_hook_v2;
        result.total_messages = msgs.length;
        result.by_type = {};
        for (const m of msgs) result.by_type[m.type] = (result.by_type[m.type]||0) + 1;
        // Unique hosts
        result.hosts = [...new Set(msgs.map(m => m.host).filter(Boolean))];
        // SFS2X binary stats (baloot host)
        const sfs = msgs.filter(m => (m.host||'').includes('baloot'));
        result.sfs_total = sfs.length;
        result.sfs_recv_with_data = sfs.filter(m => m.type === 'RECV' && Array.isArray(m.data)).length;
        // Last 3 SFS2X binary messages with header preview
        result.sfs_recent = sfs.slice(-3).map(m => ({
            type: m.type, size: m.size,
            header: Array.isArray(m.data) ? m.data.slice(0,10).map(b => b.toString(16).padStart(2,'0')).join(' ') : null,
        }));
        return result;
    }""",

    # ── 8. WebSocket Interceptor (SAFE) ─────────────────────────
    # Installs a WebSocket proxy that captures ALL traffic (SEND + RECV)
    # WITHOUT modifying binaryType. Uses Blob→ArrayBuffer async reads
    # for incoming data, preserving Unity's expected Blob format.
    "ws_interceptor": """() => {
        if (window.__ws_interceptor_v4) return {status: 'already_active', msgs: (window.__ws_messages||[]).length};

        window.__ws_messages = window.__ws_messages || [];
        window.__ws_instances = [];
        const OrigWS = window.WebSocket;

        window.WebSocket = function(url, protocols) {
            const ws = protocols ? new OrigWS(url, protocols) : new OrigWS(url);
            const ts = Date.now();
            const hostOnly = (() => { try { return new URL(url).hostname; } catch(e) { return url; } })();

            window.__ws_messages.push({type:'CONNECT', t: ts, host: hostOnly, size: 0});
            window.__ws_instances.push({ws: ws, host: hostOnly, connectedAt: ts});

            // RECV: clone Blob asynchronously — Unity handler gets the original untouched
            ws.addEventListener('message', function(evt) {
                if (evt.data instanceof Blob) {
                    const blob = evt.data;
                    const reader = new FileReader();
                    reader.onload = function() {
                        const arr = new Uint8Array(reader.result);
                        window.__ws_messages.push({
                            type: 'RECV', t: Date.now(), host: hostOnly,
                            size: arr.length, data: Array.from(arr.slice(0, 2000)),
                            complete: arr.length <= 2000, binary: true
                        });
                    };
                    reader.readAsArrayBuffer(blob);
                } else if (evt.data instanceof ArrayBuffer) {
                    const arr = new Uint8Array(evt.data);
                    window.__ws_messages.push({
                        type: 'RECV', t: Date.now(), host: hostOnly,
                        size: arr.length, data: Array.from(arr.slice(0, 2000)),
                        complete: arr.length <= 2000, binary: true
                    });
                } else {
                    window.__ws_messages.push({
                        type: 'RECV', t: Date.now(), host: hostOnly,
                        size: (evt.data||'').length, data: (evt.data||'').substring(0, 500),
                        binary: false
                    });
                }
                // Trim buffer
                if (window.__ws_messages.length > 5000) window.__ws_messages = window.__ws_messages.slice(-3000);
            });

            // SEND: intercept outgoing via .send() override
            const origSend = ws.send.bind(ws);
            ws.send = function(data) {
                const msg = {type:'SEND', t: Date.now(), host: hostOnly};
                if (data instanceof ArrayBuffer) {
                    msg.size = data.byteLength;
                    msg.data = Array.from(new Uint8Array(data).slice(0, 2000));
                    msg.complete = data.byteLength <= 2000;
                    msg.binary = true;
                } else if (data instanceof Blob) {
                    msg.size = data.size; msg.data = '[Blob]'; msg.binary = true;
                } else {
                    msg.size = (data||'').length;
                    msg.data = typeof data === 'string' ? data.substring(0, 500) : '[unknown]';
                    msg.binary = false;
                }
                window.__ws_messages.push(msg);
                return origSend(data);
            };

            ws.addEventListener('close', function(evt) {
                window.__ws_messages.push({type:'CLOSE', t: Date.now(), host: hostOnly, code: evt.code, size: 0});
            });
            ws.addEventListener('error', function() {
                window.__ws_messages.push({type:'ERROR', t: Date.now(), host: hostOnly, size: 0});
            });

            return ws;
        };
        window.WebSocket.prototype = OrigWS.prototype;
        window.WebSocket.CONNECTING = OrigWS.CONNECTING;
        window.WebSocket.OPEN = OrigWS.OPEN;
        window.WebSocket.CLOSING = OrigWS.CLOSING;
        window.WebSocket.CLOSED = OrigWS.CLOSED;
        window.__ws_interceptor_v4 = true;
        window.__ws_OrigWebSocket = OrigWS;

        return {status: 'v4_installed', note: 'Blob-safe, no binaryType change'};
    }""",

    # ── 9. Existing WS Hook (SAFE) ───────────────────────────────
    # Hooks into ALREADY-OPEN WebSocket connections (e.g., SFS2X that
    # connected before our interceptor was injected). Uses prototype
    # patching for SEND and FileReader for RECV on Blob streams.
    "ws_existing_hook": """() => {
        if (window.__ws_existing_hook_v2) return {status: 'already_active'};

        window.__ws_messages = window.__ws_messages || [];

        // Hook .send() at prototype level to capture ALL outgoing from existing WS
        const OrigSend = WebSocket.prototype.send;
        if (!window.__ws_proto_send_hooked) {
            WebSocket.prototype.send = function(data) {
                if (!this.__tracked) {
                    this.__tracked = true;
                    window.__ws_instances = window.__ws_instances || [];
                    const host = (() => { try { return new URL(this.url).hostname; } catch(e) { return '?'; } })();
                    window.__ws_instances.push({ws: this, host: host, connectedAt: Date.now()});

                    // Hook RECV via addEventListener (safe — doesn't replace onmessage)
                    this.addEventListener('message', function(evt) {
                        if (evt.data instanceof Blob) {
                            const reader = new FileReader();
                            reader.onload = function() {
                                const arr = new Uint8Array(reader.result);
                                window.__ws_messages.push({
                                    type: 'RECV', t: Date.now(), host: host,
                                    size: arr.length, data: Array.from(arr.slice(0, 2000)),
                                    complete: arr.length <= 2000, binary: true
                                });
                            };
                            reader.readAsArrayBuffer(evt.data);
                        } else if (evt.data instanceof ArrayBuffer) {
                            const arr = new Uint8Array(evt.data);
                            window.__ws_messages.push({
                                type: 'RECV', t: Date.now(), host: host,
                                size: arr.length, data: Array.from(arr.slice(0, 2000)),
                                complete: arr.length <= 2000, binary: true
                            });
                        } else {
                            window.__ws_messages.push({
                                type: 'RECV', t: Date.now(), host: host,
                                size: (evt.data||'').length, data: (evt.data||'').substring(0,500),
                                binary: false
                            });
                        }
                        if (window.__ws_messages.length > 5000) window.__ws_messages = window.__ws_messages.slice(-3000);
                    });
                }
                const host = (() => { try { return new URL(this.url).hostname; } catch(e) { return '?'; } })();
                const msg = {type:'SEND', t: Date.now(), host: host};
                if (data instanceof ArrayBuffer) {
                    msg.size = data.byteLength;
                    msg.data = Array.from(new Uint8Array(data).slice(0, 2000));
                    msg.complete = data.byteLength <= 2000;
                    msg.binary = true;
                } else if (typeof data === 'string') {
                    msg.size = data.length; msg.data = data.substring(0, 500); msg.binary = false;
                } else {
                    msg.size = 0; msg.data = '[other]'; msg.binary = true;
                }
                window.__ws_messages.push(msg);
                return OrigSend.call(this, data);
            };
            window.__ws_proto_send_hooked = true;
        }

        window.__ws_existing_hook_v2 = true;
        return {status: 'v2_installed', note: 'Blob-safe RECV via addEventListener+FileReader'};
    }""",

    # ── 10. Canvas Info ───────────────────────────────────────────
    "canvas_info": """() => {
        const canvas = document.querySelector('#unity-canvas') || document.querySelector('canvas');
        if (!canvas) return { error: 'No canvas found' };
        const result = {
            id: canvas.id || null,
            classes: canvas.className || null,
            width: canvas.width,
            height: canvas.height,
            style_width: canvas.style.width,
            style_height: canvas.style.height,
        };
        const parent = canvas.parentElement;
        if (parent) {
            result.parent_id = parent.id || null;
            result.parent_classes = parent.className || null;
        }
        return result;
    }""",
}


# ── Async API ────────────────────────────────────────────────────────

async def run_full_recon(page) -> dict:
    """Run all reconnaissance scripts and return a combined report.

    @param page: Playwright async page object.
    @returns Dict with one key per recon script, containing its result.
    """
    report = {}
    for name, script in RECON_SCRIPTS.items():
        try:
            result = await page.evaluate(script)
            report[name] = result
            logger.info(f"Recon [{name}]: {json.dumps(result, default=str)[:200]}")
        except Exception as e:
            report[name] = {"error": str(e)}
            logger.warning(f"Recon [{name}] failed: {e}")
    return report


async def save_recon_report(
    page, output_path: str = "gbaloot/recon_report.json"
) -> dict:
    """Run recon and save to a JSON file for analysis."""
    report = await run_full_recon(page)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Recon report saved to {output_path}")
    return report


# ── Sync API (for use with sync Playwright) ──────────────────────────

def run_full_recon_sync(page) -> dict:
    """Synchronous version of run_full_recon.

    @param page: Playwright sync page object.
    @returns Dict with one key per recon script.
    """
    report = {}
    for name, script in RECON_SCRIPTS.items():
        try:
            result = page.evaluate(script)
            report[name] = result
            logger.info(f"Recon [{name}]: {json.dumps(result, default=str)[:200]}")
        except Exception as e:
            report[name] = {"error": str(e)}
            logger.warning(f"Recon [{name}] failed: {e}")
    return report


def save_recon_report_sync(
    page, output_path: str = "gbaloot/recon_report.json"
) -> dict:
    """Synchronous version of save_recon_report."""
    report = run_full_recon_sync(page)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Recon report saved to {output_path}")
    return report
