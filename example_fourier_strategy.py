"""
Example Usage of Fourier Trading Strategy

This script demonstrates how to use the Fourier Trading Strategy
on real market data.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from fourier_strategy import FourierTradingStrategy


def fetch_sample_data(ticker: str = 'BTC-USD',
                     period: str = '1y',
                     interval: str = '1d') -> pd.DataFrame:
    """
    Fetch sample OHLCV data from Yahoo Finance.

    Args:
        ticker: Ticker symbol
        period: Data period ('1mo', '3mo', '6mo', '1y', '2y', etc.)
        interval: Data interval ('1d', '1h', '15m', etc.)

    Returns:
        OHLCV DataFrame
    """
    print(f"Fetching {ticker} data ({period}, {interval})...")

    df = yf.download(ticker, period=period, interval=interval, progress=False)

    # Rename columns to lowercase
    df.columns = [col.lower() for col in df.columns]

    print(f"Fetched {len(df)} data points from {df.index[0]} to {df.index[-1]}")

    return df


def generate_synthetic_data(n_points: int = 500) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data for testing.

    Args:
        n_points: Number of data points

    Returns:
        Synthetic OHLCV DataFrame
    """
    print(f"Generating {n_points} points of synthetic data...")

    # Create dates
    dates = pd.date_range(start='2023-01-01', periods=n_points, freq='D')

    # Generate price with trend + noise + cycles
    t = np.arange(n_points)

    # Trend component
    trend = 100 + 0.05 * t

    # Cyclical components (multiple frequencies)
    cycle1 = 10 * np.sin(2 * np.pi * t / 50)  # 50-day cycle
    cycle2 = 5 * np.sin(2 * np.pi * t / 20)   # 20-day cycle
    cycle3 = 3 * np.sin(2 * np.pi * t / 10)   # 10-day cycle

    # Noise
    noise = np.random.normal(0, 2, n_points)

    # Combine
    close = trend + cycle1 + cycle2 + cycle3 + noise

    # Generate OHLC from close
    high = close + np.abs(np.random.normal(1, 0.5, n_points))
    low = close - np.abs(np.random.normal(1, 0.5, n_points))
    open_ = close + np.random.normal(0, 0.5, n_points)

    # Generate volume
    volume = np.abs(np.random.normal(1000000, 200000, n_points))

    df = pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    }, index=dates)

    return df


def example_basic_usage():
    """Basic usage example with default parameters."""
    print("=" * 70)
    print("EXAMPLE 1: BASIC USAGE WITH DEFAULT PARAMETERS")
    print("=" * 70)

    # Fetch data
    df = fetch_sample_data('BTC-USD', period='1y', interval='1d')

    # Initialize strategy with default parameters
    strategy = FourierTradingStrategy()

    # Run strategy
    results = strategy.run(df, run_backtest=True, verbose=True)

    # Print summary
    print(strategy.get_summary())

    # Get current signal
    current_signal = strategy.get_current_signal()
    print(f"\nCurrent Signal: {current_signal['composite_signal']:.2f}")
    print(f"Confidence: {current_signal['confidence']:.1f}%")
    print(f"Position: {current_signal['position']}")

    # Export results
    strategy.export_results('fourier_strategy_results.csv')

    # Create visualizations
    print("\nGenerating visualizations...")
    strategy.visualize('comprehensive', save_path='fourier_strategy_analysis.png')
    strategy.visualize('performance', save_path='fourier_strategy_performance.png')

    plt.show()

    return strategy, results


def example_custom_parameters():
    """Example with custom parameters."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: CUSTOM PARAMETERS")
    print("=" * 70)

    # Fetch data
    df = fetch_sample_data('ETH-USD', period='6mo', interval='1d')

    # Custom signal weights (emphasize momentum)
    custom_weights = {
        'price_trend': 0.25,      # 25% - Price trend
        'ema_alignment': 0.25,    # 25% - EMA alignment
        'rsi': 0.05,              # 5%  - RSI
        'macd': 0.20,             # 20% - MACD (momentum)
        'volume': 0.10,           # 10% - Volume
        'stochastic': 0.05,       # 5%  - Stochastic
        'correlation': 0.05,      # 5%  - Correlation
        'phase_momentum': 0.05    # 5%  - Phase momentum
    }

    # Initialize with custom parameters
    strategy = FourierTradingStrategy(
        n_harmonics=7,                    # More harmonics (keep more detail)
        noise_threshold=0.2,              # Lower threshold (filter less)
        base_ema_period=21,               # Faster EMA base
        ema_timeframe_multipliers=[1, 2, 3, 6],  # Different timeframes
        correlation_threshold=0.6,        # Lower correlation requirement
        min_signal_strength=0.4,          # Lower entry threshold
        signal_weights=custom_weights,
        initial_capital=50000.0,
        commission=0.0015                 # 0.15% commission
    )

    # Run strategy
    results = strategy.run(df, run_backtest=True, verbose=True)

    # Print summary
    print(strategy.get_summary())

    return strategy, results


def example_synthetic_data():
    """Example with synthetic data (for controlled testing)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: SYNTHETIC DATA TESTING")
    print("=" * 70)

    # Generate synthetic data
    df = generate_synthetic_data(n_points=500)

    # Initialize strategy
    strategy = FourierTradingStrategy(
        n_harmonics=5,
        noise_threshold=0.3
    )

    # Run strategy
    results = strategy.run(df, run_backtest=True, verbose=True)

    # Print summary
    print(strategy.get_summary())

    # Visualize
    strategy.visualize('comprehensive', save_path='fourier_synthetic_analysis.png')

    return strategy, results


def example_analysis_only():
    """Example: Analysis without backtesting."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: ANALYSIS ONLY (NO BACKTEST)")
    print("=" * 70)

    # Fetch data
    df = fetch_sample_data('SPY', period='3mo', interval='1h')

    # Initialize strategy
    strategy = FourierTradingStrategy()

    # Run without backtest
    results = strategy.run(df, run_backtest=False, verbose=True)

    # Access components
    print("\nFiltered Price vs Raw Price (last 5 points):")
    print(results['output_df'][['close', 'price_filtered']].tail())

    print("\nEMA Alignment (last 5 points):")
    print(results['output_df'][['filtered_alignment_score']].tail())

    print("\nComposite Signal (last 5 points):")
    print(results['output_df'][['composite_signal', 'signal_confidence']].tail())

    # Get current signal
    current = strategy.get_current_signal()
    print(f"\nCurrent Trading Signal:")
    print(f"  Signal Strength: {current['composite_signal']:.3f}")
    print(f"  Confidence: {current['confidence']:.1f}%")
    print(f"  Recommended Position: {current['position']}")
    print(f"  Reason: {current['signal_reason']}")

    return strategy, results


def example_compare_tickers():
    """Compare strategy performance on multiple tickers."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: MULTI-TICKER COMPARISON")
    print("=" * 70)

    tickers = ['BTC-USD', 'ETH-USD', 'SPY']
    results_comparison = []

    for ticker in tickers:
        print(f"\n{'='*70}")
        print(f"Testing on {ticker}")
        print('='*70)

        try:
            df = fetch_sample_data(ticker, period='6mo', interval='1d')

            strategy = FourierTradingStrategy()
            results = strategy.run(df, run_backtest=True, verbose=False)

            metrics = results['metrics']

            results_comparison.append({
                'ticker': ticker,
                'total_return': metrics['total_return_pct'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'max_drawdown': metrics['max_drawdown_pct'],
                'win_rate': metrics['win_rate_pct'],
                'profit_factor': metrics['profit_factor'],
                'num_trades': metrics['num_trades']
            })

            print(f"\n{ticker} Results:")
            print(f"  Return: {metrics['total_return_pct']:.2f}%")
            print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
            print(f"  Max DD: {metrics['max_drawdown_pct']:.2f}%")
            print(f"  Win Rate: {metrics['win_rate_pct']:.2f}%")

        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    # Summary table
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    comparison_df = pd.DataFrame(results_comparison)
    print(comparison_df.to_string(index=False))

    return comparison_df


if __name__ == '__main__':
    # Run examples
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "FOURIER STRATEGY EXAMPLES" + " " * 28 + "║")
    print("╚" + "═" * 68 + "╝\n")

    # Choose which examples to run
    run_examples = {
        'basic': True,
        'custom': False,
        'synthetic': False,
        'analysis_only': False,
        'compare': False
    }

    if run_examples['basic']:
        strategy1, results1 = example_basic_usage()

    if run_examples['custom']:
        strategy2, results2 = example_custom_parameters()

    if run_examples['synthetic']:
        strategy3, results3 = example_synthetic_data()

    if run_examples['analysis_only']:
        strategy4, results4 = example_analysis_only()

    if run_examples['compare']:
        comparison = example_compare_tickers()

    print("\n" + "=" * 70)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 70)
