"""Quick test: run the SFS2X decoder against captured data."""
import json
import sys
sys.path.insert(0, "tools")
from game_decoder import hex_to_bytes, try_decompress, SFS2XDecoder, DecodeError

with open("captures/game_capture_v3_final_20260214_232007.json") as f:
    data = json.load(f)

traffic = data["websocket_traffic"]
binary_msgs = [m for m in traffic if str(m.get("data", "")).startswith("[hex:")]

total = len(binary_msgs)
success = 0
errors = 0
field_counts = []
sample_decoded = []

for i, m in enumerate(binary_msgs):
    raw, trunc = hex_to_bytes(m["data"])
    decompressed, was_comp = try_decompress(raw)

    try:
        decoder = SFS2XDecoder(decompressed)
        result = decoder.decode(raw_body=was_comp)

        fields = result.get("fields", {})
        decode_errors = result.get("errors", [])

        if decode_errors:
            errors += 1
            if errors <= 5:
                print(f"MSG {i}: ERRORS: {decode_errors}")
                hex_preview = " ".join(f"{b:02x}" for b in decompressed[:40])
                print(f"  hex: {hex_preview}")
        else:
            success += 1

        field_counts.append(len(fields))

        if i < 10:
            sample_decoded.append({
                "idx": i,
                "fields": fields,
                "errors": decode_errors,
                "compressed": was_comp,
            })
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"MSG {i}: EXCEPTION: {e}")
            hex_preview = " ".join(f"{b:02x}" for b in decompressed[:40])
            print(f"  hex: {hex_preview}")

print(f"\n=== RESULTS ===")
print(f"Total binary msgs: {total}")
print(f"Success (no errors): {success}")
print(f"With errors: {errors}")
print(f"Success rate: {success/total*100:.1f}%")
if field_counts:
    print(f"Avg fields: {sum(field_counts)/len(field_counts):.1f}")

# Show unique SFS command IDs (c + a fields)
from collections import Counter
cmd_ids = []
for s in sample_decoded:
    c = s["fields"].get("c")
    a = s["fields"].get("a")
    if c is not None and a is not None:
        cmd_ids.append(f"c={c},a={a}")

print(f"\n=== SAMPLE DECODED MESSAGES ===")
for s in sample_decoded:
    print(f"\nMSG {s['idx']} [compressed={s['compressed']}]:")
    print(f"  Fields: {json.dumps(s['fields'], default=str, ensure_ascii=False)[:300]}")
    if s['errors']:
        print(f"  Errors: {s['errors']}")
