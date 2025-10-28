"""
Fourier Trading Strategy Package

A sophisticated trading strategy that applies Fourier Transform filtering
to price and technical indicators for noise-free signal generation.
"""

from .strategy import FourierTradingStrategy
from .fourier_processor import FourierTransformProcessor
from .multi_timeframe_ema import MultiTimeframeEMA
from .fourier_indicators import FourierIndicators
from .correlation_analyzer import CorrelationAnalyzer
from .signal_generator import SignalGenerator
from .backtester import Backtester
from .visualizer import StrategyVisualizer

__version__ = "1.0.0"
__author__ = "Fourier Strategy Team"

__all__ = [
    'FourierTradingStrategy',
    'FourierTransformProcessor',
    'MultiTimeframeEMA',
    'FourierIndicators',
    'CorrelationAnalyzer',
    'SignalGenerator',
    'Backtester',
    'StrategyVisualizer'
]
