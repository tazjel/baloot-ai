
import os
import glob

log_dir = "logs"
files = glob.glob(os.path.join(log_dir, "*.log"))

for f in files:
    print(f"\n--- {f} ---")
    try:
        with open(f, 'rb') as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 2000), 0)
            print(fh.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        print(f"Error reading {f}: {e}")
