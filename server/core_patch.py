
import os
from py4web import core

def apply_py4web_patches():
    """
    Applies necessary monkey-patches to py4web to support
    top-level execution and custom environment paths.
    """
    def safe_module2filename(module):
        try:
            # If it's a top-level module (no dots), just return the name
            if '.' not in module:
                return module + ".py"
            # Otherwise use original logic: os.path.join(*module.split(".")[1:])
            parts = module.split(".")[1:]
            if not parts:
                return module + ".py"
            return os.path.join(*parts)
        except (TypeError, ValueError, AttributeError):
            return module
            
    # Apply Patch
    core.module2filename = safe_module2filename
