"""Find known strings in hex data and reverse-engineer the field encoding."""
import json, sys
sys.path.insert(0, "tools")
from game_decoder import hex_to_bytes, try_decompress

with open("captures/game_capture_v3_final_20260214_232007.json") as f:
    data = json.load(f)

traffic = data["websocket_traffic"]
binary_msgs = [m for m in traffic if str(m.get("data", "")).startswith("[hex:")]

# Analyze first 5 messages byte-by-byte
for i in range(min(5, len(binary_msgs))):
    raw, _ = hex_to_bytes(binary_msgs[i]["data"])
    decomp, was_comp = try_decompress(raw)
    d = binary_msgs[i].get("direction", binary_msgs[i].get("type", "?"))
    
    print(f"=== MSG {i} [{d}] len={len(decomp)} comp={was_comp} ===")
    
    # Print bytes with offset, hex, and ASCII
    for off in range(0, min(len(decomp), 120), 16):
        chunk = decomp[off:off+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"  [{off:3d}] {hex_part:<48s}  {ascii_part}")
    
    # Find readable strings (3+ printable ASCII chars in a row)
    print(f"  Strings found:")
    s = ""
    s_start = 0
    for j, b in enumerate(decomp):
        if 32 <= b < 127:
            if not s: s_start = j
            s += chr(b)
        else:
            if len(s) >= 2:
                ctx_before = " ".join(f"{decomp[max(0,s_start-4)+k]:02x}" for k in range(min(4, s_start)))
                print(f"    [{s_start:3d}] '{s}' (len={len(s)}) | before: {ctx_before}")
            s = ""
    if len(s) >= 2:
        ctx_before = " ".join(f"{decomp[max(0,s_start-4)+k]:02x}" for k in range(min(4, s_start)))
        print(f"    [{s_start:3d}] '{s}' (len={len(s)}) | before: {ctx_before}")
    print()

# Check: is byte before each string its length?
print("=== STRING LENGTH PREFIX ANALYSIS ===")
for i in range(min(20, len(binary_msgs))):
    raw, _ = hex_to_bytes(binary_msgs[i]["data"])
    decomp, _ = try_decompress(raw)
    s = ""
    s_start = 0
    for j, b in enumerate(decomp):
        if 32 <= b < 127:
            if not s: s_start = j
            s += chr(b)
        else:
            if len(s) >= 2 and s_start >= 1:
                byte_before = decomp[s_start - 1]
                match = "YES" if byte_before == len(s) else "no"
                if s_start >= 2:
                    two_before = (decomp[s_start-2] << 8) | decomp[s_start-1]
                    match2 = "YES" if two_before == len(s) else "no"
                else:
                    match2 = "?"
                print(f"  msg{i} [{s_start}] '{s[:20]}' len={len(s)} | byte[-1]=0x{byte_before:02x}({byte_before}) match1B={match} | 2B=0x{two_before:04x}({two_before}) match2B={match2}")
            s = ""
    if len(s) >= 2 and s_start >= 1:
        byte_before = decomp[s_start - 1]
        match = "YES" if byte_before == len(s) else "no"
        print(f"  msg{i} [{s_start}] '{s[:20]}' len={len(s)} | byte[-1]=0x{byte_before:02x}({byte_before}) match1B={match}")
