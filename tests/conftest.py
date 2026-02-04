import sys
import os
from unittest.mock import MagicMock

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock torch if not available
try:
    import torch
except ImportError:
    mock_torch = MagicMock()
    mock_torch.device = MagicMock()
    mock_torch.tensor = MagicMock()
    mock_torch.no_grad = MagicMock
    mock_torch.full_like = MagicMock()
    mock_torch.argmax = MagicMock()
    mock_torch.stack = MagicMock()
    mock_torch.nn.functional.softmax = MagicMock()
    mock_torch.float32 = "float32"

    # Mock nn.Module
    mock_nn = MagicMock()

    class MockModule:
        def __init__(self, *args, **kwargs):
            pass
        def to(self, device):
            return self
        def eval(self):
            return self
        def load_state_dict(self, state_dict):
            pass
        def __call__(self, *args, **kwargs):
            return MagicMock()

    mock_nn.Module = MockModule
    mock_nn.Linear = MagicMock
    mock_nn.BatchNorm1d = MagicMock
    mock_nn.Dropout = MagicMock

    mock_torch.nn = mock_nn

    sys.modules['torch'] = mock_torch
    sys.modules['torch.nn'] = mock_nn
    sys.modules['torch.nn.functional'] = MagicMock()
