"""conftest ensures the module root is importable as `app` / `ml`."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
