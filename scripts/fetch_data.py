#!/usr/bin/env python3
"""
Convenience script to fetch historical data
Run from project root: python3 fetch_data.py
"""

import sys
from pathlib import Path

# Add src to path (go up one level from scripts/)
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data.hyperliquid_fetcher import main

if __name__ == '__main__':
    main()
