"""
Quick test of fixed Fourier strategy
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter

print("=" * 70)
print("TESTING FIXED FOURIER STRATEGY")
print("=" * 70)

# Fetch data
print("\n1. Fetching data from Hyperliquid...")
adapter = HyperliquidDataAdapter(symbol='ETH')
df = adapter.fetch_ohlcv(interval='1h', days_back=30, use_checkpoint=False)

print(f"\n✅ Fetched {len(df)} candles")
print(f"   Period: {df.index[0]} to {df.index[-1]}")

# Run strategy with fixes
print("\n2. Running Fourier strategy...")
strategy = FourierTradingStrategy(
    n_harmonics=5,
    noise_threshold=0.3,
    base_ema_period=28,
    correlation_threshold=0.6,  # Lower to allow more signals
    min_signal_strength=0.3,  # Lower threshold to generate trades
    max_holding_periods=168,  # 1 week max for hourly data
    initial_capital=10000.0,
    commission=0.001
)

print("\n   Using 25% position size (conservative risk management)")
print("   Min signal strength: 0.3 (allows more trades)")
print("   Confidence threshold: 40% (lower barrier)")

results = strategy.run(df, run_backtest=True, verbose=True)

# Print summary
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(strategy.get_summary())

# Export
print("\nSaving results...")
strategy.export_results('test_fourier_results.csv')

# Try visualization
try:
    strategy.visualize('performance', save_path='test_performance.png')
    print("✅ Performance chart saved to: test_performance.png")
except Exception as e:
    print(f"⚠️  Visualization failed: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print("\nResults saved to:")
print("  - test_fourier_results.csv")
print("  - test_performance.png")
