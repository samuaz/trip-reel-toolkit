"""Shared bootstrap: put the repo root on sys.path so `import reelkit` works
no matter where the script is run from."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
