#!/usr/bin/env python3
"""
Backtest ALL 9 Harmonic Iterations (3-6-9 Convergence) - V2 HIGH WIN RATE

STRICT THRESHOLDS based on proven 85-90+ values that achieved 82-86% win rates

ALL parameters fine-tuned to Tesla's 3-6-9 harmonic convergence principles.
ALL iterations use FULL DSP: MTF FFT + Volume FFT + Fibonacci Levels
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Copy all imports from original file
import pandas as pd
import numpy as np
import json
from datetime import datetime
from fourier_strategy import FourierTradingStrategy
from fourier_strategy.fibonacci_ribbon_analyzer import FibonacciRibbonAnalyzer
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter
from src.reporting.chart_generator import ChartGenerator
from scipy.fft import fft, ifft
import webbrowser

# Define 9 harmonic iterations - STRICT THRESHOLDS for HIGH WIN RATES (85-90+)
# Based on proven values that achieved 82-86% win rates
# All values fine-tuned to 3-6-9 harmonic convergence
ITERATIONS = {
    1: {
        "name": "HARMONIC Elite (90+)",
        "compression": 90,      # 9+0=9 ✓ (STRICTEST - Proven 86% win rate!)
        "alignment": 90,        # 9+0=9 ✓
        "confluence": 63,       # 6+3=9 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.06,  # 0+6=6 ✓ (Light - quality over quantity)
        "fib_weight": 0.03,     # 0+3=3 ✓
        "description": "90/90/63 - Elite (9+9+9) - STRICTEST - Target 85%+ win rate"
    },
    2: {
        "name": "HARMONIC Premium (87+)",
        "compression": 87,      # 8+7=15 → 1+5=6 ✓
        "alignment": 87,        # 8+7=15 → 1+5=6 ✓
        "confluence": 63,       # 6+3=9 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.06,  # 0+6=6 ✓
        "fib_weight": 0.06,     # 0+6=6 ✓
        "description": "87/87/63 - Premium (6+6+9) - Very High Quality - Target 83%+ win rate"
    },
    3: {
        "name": "HARMONIC Superior (84+)",
        "compression": 84,      # 8+4=12 → 1+2=3 ✓
        "alignment": 84,        # 8+4=12 → 1+2=3 ✓
        "confluence": 63,       # 6+3=9 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.09,  # 0+9=9 ✓
        "fib_weight": 0.06,     # 0+6=6 ✓
        "description": "84/84/63 - Superior (3+3+9) - High Quality - Target 80%+ win rate"
    },
    4: {
        "name": "HARMONIC Select (81+)",
        "compression": 81,      # 8+1=9 ✓
        "alignment": 84,        # 8+4=12 → 1+2=3 ✓
        "confluence": 60,       # 6+0=6 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.09,  # 0+9=9 ✓
        "fib_weight": 0.09,     # 0+9=9 ✓
        "description": "81/84/60 - Select (9+3+6) - Selective - Target 78%+ win rate"
    },
    5: {
        "name": "HARMONIC Balanced (78+)",
        "compression": 78,      # 7+8=15 → 1+5=6 ✓
        "alignment": 81,        # 8+1=9 ✓
        "confluence": 60,       # 6+0=6 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.12,  # 1+2=3 ✓
        "fib_weight": 0.09,     # 0+9=9 ✓
        "description": "78/81/60 - Balanced (6+9+6) - Medium DSP - Target 75%+ win rate"
    },
    6: {
        "name": "HARMONIC Active (75+)",
        "compression": 75,      # 7+5=12 → 1+2=3 ✓
        "alignment": 78,        # 7+8=15 → 1+5=6 ✓
        "confluence": 60,       # 6+0=6 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.15,  # 1+5=6 ✓
        "fib_weight": 0.12,     # 1+2=3 ✓
        "description": "75/78/60 - Active (3+6+6) - More Trades - Target 72%+ win rate"
    },
    7: {
        "name": "HARMONIC Moderate (72+)",
        "compression": 72,      # 7+2=9 ✓
        "alignment": 75,        # 7+5=12 → 1+2=3 ✓
        "confluence": 60,       # 6+0=6 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.15,  # 1+5=6 ✓
        "fib_weight": 0.15,     # 1+5=6 ✓
        "description": "72/75/60 - Moderate (9+3+6) - Higher Frequency - Target 70%+ win rate"
    },
    8: {
        "name": "HARMONIC Aggressive (69+)",
        "compression": 69,      # 6+9=15 → 1+5=6 ✓
        "alignment": 72,        # 7+2=9 ✓
        "confluence": 60,       # 6+0=6 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.18,  # 1+8=9 ✓
        "fib_weight": 0.18,     # 1+8=9 ✓
        "description": "69/72/60 - Aggressive (6+9+6) - Strong DSP - Target 68%+ win rate"
    },
    9: {
        "name": "HARMONIC Maximum (66+)",
        "compression": 66,      # 6+6=12 → 1+2=3 ✓
        "alignment": 69,        # 6+9=15 → 1+5=6 ✓
        "confluence": 60,       # 6+0=6 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.21,  # 2+1=3 ✓
        "fib_weight": 0.21,     # 2+1=3 ✓
        "description": "66/69/60 - Maximum (3+6+6) - Heavy DSP - Target 65%+ win rate"
    }
}

# Import the rest of the file from original
exec(open('backtest_harmonic_iterations.py').read().split('ITERATIONS = {')[1].split('}')[1])
