"""
Create optimization comparison chart for Telegram
Generates a simple bar chart comparing optimal, backtest, and actual performance
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict
import warnings

# Suppress font glyph warnings for emojis
warnings.filterwarnings('ignore', category=UserWarning, message='.*Glyph.*missing from font.*')


def create_optimization_chart(optimal_data: Dict, backtest_data: Dict, actual_data: Dict,
                              output_path: str = 'trading_data/optimization_chart.png') -> str:
    """
    Create a comparison chart for optimization results

    Args:
        optimal_data: Dict with optimal trades stats
        backtest_data: Dict with backtest trades stats
        actual_data: Dict with actual trades stats
        output_path: Where to save the chart

    Returns:
        Path to saved chart
    """
    # Extract metrics
    categories = ['Optimal\n(Perfect)', 'Backtest\n(Rules)', 'Actual\n(Live)']

    trades = [
        optimal_data.get('total_trades', 0),
        backtest_data.get('total_trades', 0),
        actual_data.get('total_trades', 0)
    ]

    pnl = [
        optimal_data.get('total_pnl_pct', 0),
        backtest_data.get('total_pnl_pct', 0),
        actual_data.get('total_pnl_pct', 0)
    ]

    avg_pnl = [
        optimal_data.get('avg_pnl_pct', 0),
        backtest_data.get('avg_pnl_pct', 0),
        actual_data.get('avg_pnl_per_trade', 0)
    ]

    win_rate = [
        optimal_data.get('win_rate', 1.0) * 100,
        backtest_data.get('win_rate', 0) * 100,
        actual_data.get('win_rate', 0) * 100
    ]

    # Create figure with 2x2 subplots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('🔧 Optimization Cycle: 3-Way Performance Comparison',
                 fontsize=16, fontweight='bold', y=0.995)

    # Colors
    colors = ['#2ecc71', '#3498db', '#e74c3c']  # Green, Blue, Red

    # 1. Total Trades
    bars1 = ax1.bar(categories, trades, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Number of Trades', fontweight='bold')
    ax1.set_title('📊 Total Trades', fontweight='bold', pad=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    for i, (bar, val) in enumerate(zip(bars1, trades)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(val)}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # 2. Total PnL %
    bars2 = ax2.bar(categories, pnl, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('Total PnL (%)', fontweight='bold')
    ax2.set_title('💰 Total PnL %', fontweight='bold', pad=10)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    for i, (bar, val) in enumerate(zip(bars2, pnl)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:+.2f}%',
                ha='center', va='bottom' if val > 0 else 'top',
                fontweight='bold', fontsize=11)

    # 3. Avg PnL per Trade
    bars3 = ax3.bar(categories, avg_pnl, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax3.set_ylabel('Avg PnL per Trade (%)', fontweight='bold')
    ax3.set_title('📈 Avg PnL per Trade', fontweight='bold', pad=10)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    for i, (bar, val) in enumerate(zip(bars3, avg_pnl)):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:+.2f}%',
                ha='center', va='bottom' if val > 0 else 'top',
                fontweight='bold', fontsize=11)

    # 4. Win Rate
    bars4 = ax4.bar(categories, win_rate, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax4.set_ylabel('Win Rate (%)', fontweight='bold')
    ax4.set_title('🎯 Win Rate', fontweight='bold', pad=10)
    ax4.set_ylim([0, 105])
    ax4.grid(axis='y', alpha=0.3, linestyle='--')
    for i, (bar, val) in enumerate(zip(bars4, win_rate)):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Add summary text
    gap_trades = optimal_data.get('total_trades', 0) - backtest_data.get('total_trades', 0)
    gap_pnl = optimal_data.get('total_pnl_pct', 0) - backtest_data.get('total_pnl_pct', 0)
    capture_rate = (backtest_data.get('total_trades', 0) / max(optimal_data.get('total_trades', 1), 1)) * 100

    summary_text = f"""
    📋 Summary:
    • Capture Rate: {capture_rate:.1f}% (catching {backtest_data.get('total_trades', 0)}/{optimal_data.get('total_trades', 0)} optimal setups)
    • Gap to Close: {gap_trades} trades, {gap_pnl:+.2f}% PnL
    • Optimization Goal: Improve rules to close the gap
    """

    fig.text(0.5, 0.02, summary_text.strip(), ha='center', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # Adjust layout and save
    plt.tight_layout(rect=[0, 0.06, 1, 0.98])
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    print(f"✅ Chart saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    # Test the chart generator
    test_optimal = {
        'total_trades': 45,
        'total_pnl_pct': 12.5,
        'avg_pnl_pct': 0.28,
        'win_rate': 1.0
    }

    test_backtest = {
        'total_trades': 28,
        'total_pnl_pct': 6.2,
        'avg_pnl_pct': 0.22,
        'win_rate': 0.68
    }

    test_actual = {
        'total_trades': 22,
        'total_pnl_pct': 4.8,
        'avg_pnl_per_trade': 0.22,
        'win_rate': 0.64
    }

    create_optimization_chart(test_optimal, test_backtest, test_actual)
    print("✅ Test chart created!")
