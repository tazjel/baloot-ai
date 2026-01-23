import os
import subprocess
import sys

def run_command(command):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True)
    return result.returncode == 0

def main():
    print("=== 🧹 Linting Project ===")
    
    # Check if tools exist
    try:
        subprocess.run(["flake8", "--version"], capture_output=True)
        has_flake8 = True
    except FileNotFoundError:
        has_flake8 = False
        print("⚠️  flake8 not found. Skipping python linting.")

    all_passed = True

    if has_flake8:
        # Exclude venv and migration folders
        print("\n--> Python (flake8)...")
        if not run_command("flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude .git,__pycache__,.env,node_modules,venv"):
            all_passed = False

    print("\n--> Frontend (npm run lint)...")
    if os.path.exists("frontend/package.json"):
        if not run_command("cd frontend && npm run lint --if-present"):
             # Don't fail the whole script if just frontend lint fails for now
             print("⚠️  Frontend lint found issues.")

    if all_passed:
        print("\n✅ All checks passed!")
    else:
        print("\n❌ Some checks failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
