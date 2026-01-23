import argparse
import re
from datetime import datetime
import sys
import os
import glob

def parse_args():
    parser = argparse.ArgumentParser(description='Analyze game logs for lag and errors.')
    parser.add_argument('--file', type=str, help='Path to the log file')
    parser.add_argument('--latest', action='store_true', help='Analyze the most recently modified log file in logs/')
    parser.add_argument('--threshold', type=float, default=2.0, help='Time threshold for lag detection in seconds')
    return parser.parse_args()

def get_latest_log_file(log_dir="logs"):
    try:
        list_of_files = glob.glob(os.path.join(log_dir, "*.log"))
        if not list_of_files:
            return None
        latest_file = max(list_of_files, key=os.path.getmtime)
        return latest_file
    except Exception as e:
        print(f"Error finding latest log: {e}")
        return None

def parse_timestamp(line):
    # Regex for standard python logging: 2026-01-12 23:29:43,456
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
    return None

def analyze_log(file_path, threshold):
    print(f"--- Analyzing {file_path} (Lag Threshold: {threshold}s) ---")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return

    prev_time = None
    lag_count = 0
    error_count = 0
    warnings = []
    
    for i, line in enumerate(lines):
        # 1. Error Detection
        if "ERROR" in line or "Traceback" in line or "Exception" in line:
            error_count += 1
            print(f"[LINE {i+1}] {line.strip()}")
        
        if "WARNING" in line:
            warnings.append(f"[LINE {i+1}] {line.strip()}")

        # 2. Lag Detection
        curr_time = parse_timestamp(line)
        if curr_time:
            if prev_time:
                delta = (curr_time - prev_time).total_seconds()
                if delta > threshold:
                    lag_count += 1
                    print(f"\n>>> LONG PAUSE DETECTED ({delta:.2f}s) <<<")
                    print(f"    From: [Line {i}] {lines[i-1].strip()}")
                    print(f"    To:   [Line {i+1}] {line.strip()}\n")
            prev_time = curr_time

    print("-" * 40)
    print(f"Analysis Complete.")
    print(f"Total Errors: {error_count}")
    print(f"Total Long Pauses (> {threshold}s): {lag_count}")
    
    if warnings:
        print(f"Total Warnings: {len(warnings)}")
        # print("First 5 Warnings:")
        # for w in warnings[:5]:
        #     print(w)

if __name__ == "__main__":
    args = parse_args()
    
    target_file = args.file
    
    if args.latest:
        found_file = get_latest_log_file()
        if found_file:
            print(f"Found latest log: {found_file}")
            target_file = found_file
        else:
            print("Error: No log files found in logs/ directory.")
            sys.exit(1)
            
    if not target_file:
        print("Error: You must specify --file <path> OR --latest")
        sys.exit(1)
        
    analyze_log(target_file, args.threshold)
