"""
Compare Fourier Strategy vs Traditional (Raw) Strategy

This script compares the performance of the Fourier-filtered strategy
against a traditional strategy using raw indicators.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.backtester import Backtester


class TraditionalStrategy:
    """
    Traditional strategy using raw (non-Fourier) indicators.

    This serves as a baseline for comparison.
    """

    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.backtester = Backtester(initial_capital=initial_capital)

    def calculate_traditional_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate signals using raw indicators."""
        signals = pd.DataFrame(index=df.index)

        # Simple EMA crossover
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # Simple rule-based signals
        # LONG: EMA cross up + RSI not overbought + MACD > 0
        long_signal = (
            (ema_fast > ema_slow) &
            (ema_fast.shift(1) <= ema_slow.shift(1)) &  # Crossover
            (rsi < 70) &
            (macd_line > 0)
        )

        # SHORT: EMA cross down + RSI not oversold + MACD < 0
        short_signal = (
            (ema_fast < ema_slow) &
            (ema_fast.shift(1) >= ema_slow.shift(1)) &  # Crossover
            (rsi > 30) &
            (macd_line < 0)
        )

        # Generate position signals
        position = pd.Series(0, index=df.index)

        for i in range(1, len(df)):
            if long_signal.iloc[i]:
                position.iloc[i] = 1
            elif short_signal.iloc[i]:
                position.iloc[i] = -1
            else:
                # Hold previous position
                position.iloc[i] = position.iloc[i-1]

                # Exit conditions
                if position.iloc[i] == 1 and (rsi.iloc[i] > 70 or ema_fast.iloc[i] < ema_slow.iloc[i]):
                    position.iloc[i] = 0
                elif position.iloc[i] == -1 and (rsi.iloc[i] < 30 or ema_fast.iloc[i] > ema_slow.iloc[i]):
                    position.iloc[i] = 0

        signals['position'] = position
        signals['trade_signal'] = position.diff().fillna(0)

        return signals

    def run(self, df: pd.DataFrame) -> Dict:
        """Run traditional strategy."""
        # Generate signals
        signals = self.calculate_traditional_signals(df)

        # Backtest
        backtest_results = self.backtester.run_backtest(
            df['close'],
            signals,
            position_size=1.0,
            verbose=False
        )

        return {
            'signals': signals,
            'backtest_results': backtest_results['backtest_results'],
            'metrics': backtest_results['metrics'],
            'trade_log': backtest_results['trade_log']
        }


def compare_strategies(ticker: str = 'BTC-USD',
                      period: str = '1y',
                      interval: str = '1d') -> Dict:
    """
    Compare Fourier vs Traditional strategy.

    Args:
        ticker: Ticker symbol
        period: Data period
        interval: Data interval

    Returns:
        Dictionary with comparison results
    """
    print("=" * 70)
    print(f"COMPARING STRATEGIES: {ticker}")
    print("=" * 70)

    # Fetch data
    print(f"\nFetching {ticker} data...")
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    df.columns = [col.lower() for col in df.columns]

    print(f"Data: {len(df)} points from {df.index[0]} to {df.index[-1]}")

    # Run Fourier Strategy
    print("\n[1/2] Running Fourier Strategy...")
    fourier_strategy = FourierTradingStrategy(initial_capital=10000.0)
    fourier_results = fourier_strategy.run(df, run_backtest=True, verbose=False)

    # Run Traditional Strategy
    print("[2/2] Running Traditional Strategy...")
    traditional_strategy = TraditionalStrategy(initial_capital=10000.0)
    traditional_results = traditional_strategy.run(df)

    # Compare metrics
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    fourier_metrics = fourier_results['metrics']
    traditional_metrics = traditional_results['metrics']

    comparison = pd.DataFrame({
        'Fourier Strategy': [
            fourier_metrics['total_return_pct'],
            fourier_metrics['annualized_return_pct'],
            fourier_metrics['sharpe_ratio'],
            fourier_metrics['max_drawdown_pct'],
            fourier_metrics['win_rate_pct'],
            fourier_metrics['profit_factor'],
            fourier_metrics['num_trades']
        ],
        'Traditional Strategy': [
            traditional_metrics['total_return_pct'],
            traditional_metrics['annualized_return_pct'],
            traditional_metrics['sharpe_ratio'],
            traditional_metrics['max_drawdown_pct'],
            traditional_metrics['win_rate_pct'],
            traditional_metrics['profit_factor'],
            traditional_metrics['num_trades']
        ]
    }, index=[
        'Total Return (%)',
        'Annualized Return (%)',
        'Sharpe Ratio',
        'Max Drawdown (%)',
        'Win Rate (%)',
        'Profit Factor',
        'Number of Trades'
    ])

    # Calculate improvement
    comparison['Improvement (%)'] = (
        (comparison['Fourier Strategy'] - comparison['Traditional Strategy']) /
        comparison['Traditional Strategy'].abs() * 100
    )

    print("\n" + comparison.to_string())

    # Determine winner
    print("\n" + "=" * 70)
    print("WINNER ANALYSIS")
    print("=" * 70)

    metrics_to_compare = {
        'Total Return': (fourier_metrics['total_return_pct'], traditional_metrics['total_return_pct'], 'higher'),
        'Sharpe Ratio': (fourier_metrics['sharpe_ratio'], traditional_metrics['sharpe_ratio'], 'higher'),
        'Max Drawdown': (fourier_metrics['max_drawdown_pct'], traditional_metrics['max_drawdown_pct'], 'lower'),
        'Win Rate': (fourier_metrics['win_rate_pct'], traditional_metrics['win_rate_pct'], 'higher'),
        'Profit Factor': (fourier_metrics['profit_factor'], traditional_metrics['profit_factor'], 'higher')
    }

    fourier_wins = 0
    traditional_wins = 0

    for metric_name, (fourier_val, trad_val, better) in metrics_to_compare.items():
        if better == 'higher':
            winner = "Fourier" if fourier_val > trad_val else "Traditional"
        else:
            winner = "Fourier" if fourier_val < abs(trad_val) else "Traditional"

        if winner == "Fourier":
            fourier_wins += 1
        else:
            traditional_wins += 1

        print(f"{metric_name:20s} - Winner: {winner:12s} ({fourier_val:.2f} vs {trad_val:.2f})")

    print(f"\nOverall: Fourier wins {fourier_wins}/5 metrics")

    return {
        'ticker': ticker,
        'fourier_results': fourier_results,
        'traditional_results': traditional_results,
        'comparison_table': comparison,
        'fourier_wins': fourier_wins,
        'traditional_wins': traditional_wins
    }


def plot_comparison(comparison_data: Dict, save_path: str = None):
    """
    Plot side-by-side comparison.

    Args:
        comparison_data: Results from compare_strategies
        save_path: Optional save path
    """
    fourier_results = comparison_data['fourier_results']
    traditional_results = comparison_data['traditional_results']

    fig, axes = plt.subplots(3, 2, figsize=(16, 12))

    # Equity curves
    ax1 = axes[0, 0]
    ax1.plot(fourier_results['backtest_results'].index,
            fourier_results['backtest_results']['equity'],
            label='Fourier Strategy', linewidth=2, color='blue')
    ax1.plot(traditional_results['backtest_results'].index,
            traditional_results['backtest_results']['equity'],
            label='Traditional Strategy', linewidth=2, color='red', alpha=0.7)
    ax1.set_title('Equity Curve Comparison', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Equity ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Drawdown comparison
    ax2 = axes[0, 1]
    fourier_equity = fourier_results['backtest_results']['equity']
    trad_equity = traditional_results['backtest_results']['equity']

    fourier_dd = (fourier_equity - fourier_equity.cummax()) / fourier_equity.cummax() * 100
    trad_dd = (trad_equity - trad_equity.cummax()) / trad_equity.cummax() * 100

    ax2.fill_between(fourier_dd.index, 0, fourier_dd, alpha=0.5, color='blue', label='Fourier')
    ax2.fill_between(trad_dd.index, 0, trad_dd, alpha=0.5, color='red', label='Traditional')
    ax2.set_title('Drawdown Comparison', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Drawdown (%)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Returns distribution
    ax3 = axes[1, 0]
    fourier_returns = fourier_results['backtest_results']['returns'].dropna()
    trad_returns = traditional_results['backtest_results']['returns'].dropna()

    ax3.hist(fourier_returns, bins=50, alpha=0.6, color='blue', label='Fourier', edgecolor='black')
    ax3.hist(trad_returns, bins=50, alpha=0.6, color='red', label='Traditional', edgecolor='black')
    ax3.axvline(x=0, color='black', linestyle='--', linewidth=2)
    ax3.set_title('Returns Distribution', fontweight='bold', fontsize=12)
    ax3.set_xlabel('Returns')
    ax3.set_ylabel('Frequency')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Metrics comparison bar chart
    ax4 = axes[1, 1]
    comparison_df = comparison_data['comparison_table']

    metrics_to_plot = ['Total Return (%)', 'Sharpe Ratio', 'Win Rate (%)']
    x = np.arange(len(metrics_to_plot))
    width = 0.35

    fourier_vals = [comparison_df.loc[m, 'Fourier Strategy'] for m in metrics_to_plot]
    trad_vals = [comparison_df.loc[m, 'Traditional Strategy'] for m in metrics_to_plot]

    ax4.bar(x - width/2, fourier_vals, width, label='Fourier', color='blue', alpha=0.7)
    ax4.bar(x + width/2, trad_vals, width, label='Traditional', color='red', alpha=0.7)

    ax4.set_title('Key Metrics Comparison', fontweight='bold', fontsize=12)
    ax4.set_xticks(x)
    ax4.set_xticklabels([m.split('(')[0].strip() for m in metrics_to_plot], rotation=15)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')

    # Cumulative returns
    ax5 = axes[2, 0]
    fourier_cum_returns = (1 + fourier_returns).cumprod() - 1
    trad_cum_returns = (1 + trad_returns).cumprod() - 1

    ax5.plot(fourier_cum_returns.index, fourier_cum_returns * 100,
            label='Fourier', linewidth=2, color='blue')
    ax5.plot(trad_cum_returns.index, trad_cum_returns * 100,
            label='Traditional', linewidth=2, color='red', alpha=0.7)
    ax5.set_title('Cumulative Returns', fontweight='bold', fontsize=12)
    ax5.set_ylabel('Cumulative Returns (%)')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # Trade count comparison
    ax6 = axes[2, 1]
    trade_counts = [
        fourier_results['metrics']['num_trades'],
        traditional_results['metrics']['num_trades']
    ]
    colors = ['blue', 'red']

    ax6.bar(['Fourier', 'Traditional'], trade_counts, color=colors, alpha=0.7)
    ax6.set_title('Number of Trades', fontweight='bold', fontsize=12)
    ax6.set_ylabel('Count')
    ax6.grid(True, alpha=0.3, axis='y')

    # Add values on bars
    for i, v in enumerate(trade_counts):
        ax6.text(i, v, str(v), ha='center', va='bottom', fontweight='bold')

    plt.suptitle(f"Fourier vs Traditional Strategy - {comparison_data['ticker']}",
                fontsize=16, fontweight='bold')
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

    return fig


def multi_ticker_comparison(tickers: list,
                            period: str = '1y',
                            interval: str = '1d') -> pd.DataFrame:
    """
    Compare strategies across multiple tickers.

    Args:
        tickers: List of ticker symbols
        period: Data period
        interval: Data interval

    Returns:
        Summary DataFrame
    """
    print("=" * 70)
    print("MULTI-TICKER COMPARISON")
    print("=" * 70)

    summary = []

    for ticker in tickers:
        print(f"\nProcessing {ticker}...")

        try:
            comparison = compare_strategies(ticker, period, interval)

            summary.append({
                'Ticker': ticker,
                'Fourier Return (%)': comparison['fourier_results']['metrics']['total_return_pct'],
                'Traditional Return (%)': comparison['traditional_results']['metrics']['total_return_pct'],
                'Fourier Sharpe': comparison['fourier_results']['metrics']['sharpe_ratio'],
                'Traditional Sharpe': comparison['traditional_results']['metrics']['sharpe_ratio'],
                'Fourier Wins': comparison['fourier_wins'],
                'Traditional Wins': comparison['traditional_wins']
            })

        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    summary_df = pd.DataFrame(summary)

    print("\n" + "=" * 70)
    print("MULTI-TICKER SUMMARY")
    print("=" * 70)
    print(summary_df.to_string(index=False))

    # Overall statistics
    fourier_total_wins = summary_df['Fourier Wins'].sum()
    trad_total_wins = summary_df['Traditional Wins'].sum()

    print(f"\nOverall: Fourier wins {fourier_total_wins} metrics across all tickers")
    print(f"         Traditional wins {trad_total_wins} metrics across all tickers")

    return summary_df


if __name__ == '__main__':
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "FOURIER VS TRADITIONAL COMPARISON" + " " * 23 + "║")
    print("╚" + "═" * 68 + "╝\n")

    # Single ticker comparison
    print("\n1. Single Ticker Comparison")
    print("-" * 70)

    comparison = compare_strategies('BTC-USD', period='1y', interval='1d')

    # Plot comparison
    print("\nGenerating comparison plots...")
    plot_comparison(comparison, save_path='fourier_vs_traditional_comparison.png')

    # Multi-ticker comparison
    print("\n\n2. Multi-Ticker Comparison")
    print("-" * 70)

    tickers = ['BTC-USD', 'ETH-USD', 'SPY']
    summary = multi_ticker_comparison(tickers, period='6mo', interval='1d')

    # Save summary
    summary.to_csv('multi_ticker_comparison.csv', index=False)
    print("\nSummary saved to: multi_ticker_comparison.csv")

    plt.show()

    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)
