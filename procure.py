#!/usr/bin/env python3
"""
ProcureAgent interactive CLI application entrypoint.
Usage:
  procure-agent
  python -m procure
  python procure.py
"""
import sys
from procure.cli import main

if __name__ == "__main__":
    main()
