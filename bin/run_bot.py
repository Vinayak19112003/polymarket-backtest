#!/usr/bin/env python3
"""Run the Polymarket trading bot."""

import os
import sys

# Add project root to python path (parent of bin/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.main import main

if __name__ == "__main__":
    main()
