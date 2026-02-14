"""Byte-by-byte analysis of the protocol TLV field encoding."""
import json
import sys
sys.path.insert(0, "tools")
from game_decoder import hex_to_bytes, try_decompress

with open("captures/game_capture_v3_final_20260214_232007.json") as f:
    data = json.load(f)

traffic = data["websocket_traffic"]
binary_msgs = [m for m in traffic if str(m.get("data", "")).startswith("[hex:")]

# Examine the byte-by-byte structure of 0x80 messages
print("=== BYTE-LEVEL ANALYSIS OF FIRST 15 MESSAGES ===")
print()
for i, m in enumerate(binary_msgs[:15]):
    raw, trunc = hex_to_bytes(m["data"])
    raw, was_comp = try_decompress(raw)
    d = m.get("direction", m.get("type", "?"))
    
    print(f"--- MSG {i} [{d}] len={len(raw)} comp={was_comp} ---")
    # Show all bytes with annotations
    hex_all = " ".join(f"{b:02x}" for b in raw[:80])
    print(f"  Hex: {hex_all}")
    
    # Parse manually
    pos = 0
    if not was_comp and raw[0] == 0x80:
        msg_id = int.from_bytes(raw[1:3], 'big')
        print(f"  [0] 0x80 header")
        print(f"  [1-2] msg_id = 0x{msg_id:04x} ({msg_id})")
        pos = 3
    
    # After header, should be TLV body
    print(f"  [body starts at {pos}]")
    # What does the Thrift field header look like?
    # In Thrift Binary Protocol, field header is: type(1B) + field_id(2B)
    # So: 12 00 03 could mean type=0x12(struct) field_id=0x0003
    # Then nested struct has: field_type(1B) field_id(2B) for each field
    # Until type=0x00 (STOP)
    
    # Let's try Thrift Binary Protocol interpretation
    print(f"  Thrift interpretation:")
    while pos < min(len(raw), 60):
        if raw[pos] == 0x00:  # STOP
            print(f"    [{pos}] STOP (0x00)")
            pos += 1
            break
        type_code = raw[pos]
        if pos + 2 < len(raw):
            field_id = int.from_bytes(raw[pos+1:pos+3], 'big')
            type_names = {
                0x01: "void", 0x02: "bool", 0x03: "byte/i8", 0x04: "double",
                0x06: "i16", 0x08: "i32", 0x0a: "i64", 0x0b: "string",
                0x0c: "struct", 0x0d: "map", 0x0e: "set", 0x0f: "list",
            }
            tn = type_names.get(type_code, f"0x{type_code:02x}?")
            print(f"    [{pos}] type={tn} field_id={field_id}")
            pos += 3
            
            # Read value preview
            if type_code == 0x0c:  # struct
                print(f"      -> nested struct begins")
            elif type_code == 0x0b:  # string
                if pos + 3 < len(raw):
                    slen = int.from_bytes(raw[pos:pos+4], 'big')
                    if 0 < slen < 500 and pos + 4 + slen <= len(raw):
                        sval = raw[pos+4:pos+4+slen]
                        try:
                            print(f"      -> string len={slen}: '{sval.decode('utf-8')}'")
                        except:
                            print(f"      -> string len={slen}: (binary)")
                        pos += 4 + slen
                    else:
                        print(f"      -> string len={slen} (too big or invalid)")
                        break
            elif type_code == 0x08:  # i32
                if pos + 3 < len(raw):
                    val = int.from_bytes(raw[pos:pos+4], 'big', signed=True)
                    print(f"      -> i32 = {val}")
                    pos += 4
            elif type_code == 0x02:  # bool
                if pos < len(raw):
                    print(f"      -> bool = {raw[pos]}")
                    pos += 1
            elif type_code == 0x06:  # i16
                if pos + 1 < len(raw):
                    val = int.from_bytes(raw[pos:pos+2], 'big', signed=True)
                    print(f"      -> i16 = {val}")
                    pos += 2
            elif type_code == 0x0a:  # i64
                if pos + 7 < len(raw):
                    val = int.from_bytes(raw[pos:pos+8], 'big', signed=True)
                    print(f"      -> i64 = {val}")
                    pos += 8
            else:
                break
        else:
            break
    print()
