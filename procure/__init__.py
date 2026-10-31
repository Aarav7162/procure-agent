"""
ProcureAgent Package
Autonomous AI capability procurement and programmatic settlement network.
"""
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

__version__ = "1.0.0"
