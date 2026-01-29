import py4web
import py4web.core
from py4web import action

print("--- py4web ---")
print(dir(py4web))

print("\n--- py4web.core ---")
print(dir(py4web.core))

print("\n--- action ---")
print(dir(action))

# PATCH logic from server/main.py
from py4web import core
import os

def safe_module2filename(module):
    try:
        if '.' not in module:
            return module + ".py"
        parts = module.split(".")[1:]
        if not parts:
            return module + ".py"
        return os.path.join(*parts)
    except:
        return module
        
core.module2filename = safe_module2filename

@action("test_route", method=["GET"])
def test_func():
    return "ok"

print(f"\nAction Registered? {len(action.registered)}")
if action.registered:
    act = action.registered[0]
    print(f"Action Object: {act}")
    print(f"Dir: {dir(act)}")
    print(f"Path: {getattr(act, 'path', 'N/A')}")
    print(f"Method: {getattr(act, 'method', 'N/A')}")
    print(f"Func: {getattr(act, 'f', 'N/A')}")
    print(f"Is it callable? {callable(act)}")
