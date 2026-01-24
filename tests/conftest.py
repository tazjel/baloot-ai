import sys
import os

# Add the project root directory to sys.path
# This ensures that tests in this directory can import modules from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
