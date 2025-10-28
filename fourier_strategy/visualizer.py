"""
Visualization Tools for Fourier Strategy

This module provides comprehensive visualization including
multi-panel charts, correlation heatmaps, and performance plots.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')


class StrategyVisualizer:
    """
    Visualization tools for Fourier-based trading strategy.

    Features:
    - Multi-panel charts
    - Correlation heatmaps
    - Performance visualization
    - Trade markers
    """

    def __init__(self, figsize: tuple = (16, 20), style: str = 'seaborn-v0_8-darkgrid'):
        """
        Initialize Visualizer.

        Args:
            figsize: Figure size (width, height)
            style: Matplotlib style
        """
        self.figsize = figsize
        try:
            plt.style.use(style)
        except:
            plt.style.use('default')

    def plot_comprehensive_analysis(self,
                                   price: pd.Series,
                                   price_filtered: pd.Series,
                                   ema_results: Dict,
                                   indicators: pd.DataFrame,
                                   trade_signals: pd.DataFrame,
                                   backtest_results: pd.DataFrame,
                                   correlation_matrix: pd.DataFrame,
                                   trade_log: pd.DataFrame = None,
                                   save_path: str = None):
        """
        Create comprehensive multi-panel visualization.

        Args:
            price: Raw price series
            price_filtered: Filtered price series
            ema_results: EMA analysis results
            indicators: All indicators DataFrame
            trade_signals: Trade signals DataFrame
            backtest_results: Backtest results
            correlation_matrix: Correlation matrix
            trade_log: Optional trade log
            save_path: Optional path to save figure
        """
        # Clean all data to avoid matplotlib errors
        price = price.replace([np.inf, -np.inf], np.nan).ffill().bfill()
        price_filtered = price_filtered.replace([np.inf, -np.inf], np.nan).ffill().bfill()

        # Clean indicators DataFrame
        indicators = indicators.replace([np.inf, -np.inf], np.nan).ffill().bfill()

        # Clean backtest results
        if backtest_results is not None:
            backtest_results = backtest_results.replace([np.inf, -np.inf], np.nan).ffill().bfill()

        # Clean trade signals
        trade_signals = trade_signals.replace([np.inf, -np.inf], np.nan).fillna(0)

        fig = plt.figure(figsize=self.figsize)
        gs = fig.add_gridspec(7, 2, hspace=0.3, wspace=0.3)

        # Panel 1: Price with entries/exits (spans both columns)
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_price_with_trades(ax1, price, price_filtered, trade_signals, trade_log)

        # Panel 2: EMA Ribbon
        ax2 = fig.add_subplot(gs[1, :])
        self._plot_ema_ribbon(ax2, price, ema_results)

        # Panel 3: RSI
        ax3 = fig.add_subplot(gs[2, 0])
        self._plot_rsi(ax3, indicators)

        # Panel 4: MACD
        ax4 = fig.add_subplot(gs[2, 1])
        self._plot_macd(ax4, indicators)

        # Panel 5: Volume
        ax5 = fig.add_subplot(gs[3, 0])
        self._plot_volume(ax5, indicators)

        # Panel 6: Stochastic
        ax6 = fig.add_subplot(gs[3, 1])
        self._plot_stochastic(ax6, indicators)

        # Panel 7: Correlation Heatmap
        ax7 = fig.add_subplot(gs[4, :])
        self._plot_correlation_heatmap(ax7, correlation_matrix)

        # Panel 8: Equity Curve
        ax8 = fig.add_subplot(gs[5, :])
        self._plot_equity_curve(ax8, backtest_results)

        # Panel 9: Signal Strength
        ax9 = fig.add_subplot(gs[6, :])
        self._plot_signal_strength(ax9, trade_signals)

        plt.suptitle('Fourier Strategy Comprehensive Analysis', fontsize=16, fontweight='bold')

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def _plot_price_with_trades(self,
                               ax,
                               price: pd.Series,
                               price_filtered: pd.Series,
                               trade_signals: pd.DataFrame,
                               trade_log: pd.DataFrame = None):
        """Plot price with raw and filtered signals plus trade markers."""
        # Plot prices
        ax.plot(price.index, price, label='Raw Price', alpha=0.5, linewidth=1)
        ax.plot(price_filtered.index, price_filtered, label='Filtered Price',
                linewidth=2, color='blue')

        # Mark trades
        long_entries = trade_signals[trade_signals['trade_signal'] > 0].index
        short_entries = trade_signals[trade_signals['trade_signal'] < 0].index

        if len(long_entries) > 0:
            ax.scatter(long_entries, price.loc[long_entries],
                      marker='^', color='green', s=100, label='Long Entry', zorder=5)

        if len(short_entries) > 0:
            ax.scatter(short_entries, price.loc[short_entries],
                      marker='v', color='red', s=100, label='Short Entry', zorder=5)

        ax.set_title('Price (Raw vs Filtered) with Entry/Exit Signals', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

    def _plot_ema_ribbon(self, ax, price: pd.Series, ema_results: Dict):
        """Plot EMA ribbon with raw and filtered EMAs."""
        if 'emas' not in ema_results or 'filtered_emas' not in ema_results:
            ax.text(0.5, 0.5, 'No EMA data available', ha='center', va='center')
            return

        # Plot price
        ax.plot(price.index, price, label='Price', linewidth=2, color='black', alpha=0.7)

        # Plot filtered EMAs
        emas_df = ema_results['filtered_emas']
        colors = ['blue', 'green', 'orange', 'red']

        for i, col in enumerate(emas_df.columns):
            color = colors[i % len(colors)]
            ax.plot(emas_df.index, emas_df[col], label=col, linewidth=1.5,
                   alpha=0.7, color=color)

        ax.set_title('Multi-Timeframe EMA Ribbon (Filtered)', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)

    def _plot_rsi(self, ax, indicators: pd.DataFrame):
        """Plot RSI with raw and filtered."""
        if 'rsi_raw' not in indicators.columns:
            ax.text(0.5, 0.5, 'No RSI data', ha='center', va='center')
            return

        ax.plot(indicators.index, indicators['rsi_raw'],
               label='RSI Raw', alpha=0.4, linewidth=1)
        ax.plot(indicators.index, indicators['rsi_filtered'],
               label='RSI Filtered', linewidth=2, color='blue')

        ax.axhline(y=70, color='r', linestyle='--', alpha=0.5, label='Overbought')
        ax.axhline(y=30, color='g', linestyle='--', alpha=0.5, label='Oversold')
        ax.axhline(y=50, color='gray', linestyle='-', alpha=0.3)

        ax.set_title('RSI (Raw vs Filtered)', fontweight='bold')
        ax.set_ylabel('RSI')
        ax.set_ylim([0, 100])
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)

    def _plot_macd(self, ax, indicators: pd.DataFrame):
        """Plot MACD with filtered signals."""
        if 'macd_filtered' not in indicators.columns:
            ax.text(0.5, 0.5, 'No MACD data', ha='center', va='center')
            return

        ax.plot(indicators.index, indicators['macd_filtered'],
               label='MACD Filtered', linewidth=2, color='blue')
        ax.plot(indicators.index, indicators['signal_filtered'],
               label='Signal Filtered', linewidth=2, color='red')

        # Histogram
        colors = ['green' if x > 0 else 'red' for x in indicators['histogram_filtered']]
        ax.bar(indicators.index, indicators['histogram_filtered'],
              label='Histogram', alpha=0.3, color=colors)

        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        ax.set_title('MACD (Filtered)', fontweight='bold')
        ax.set_ylabel('MACD')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)

    def _plot_volume(self, ax, indicators: pd.DataFrame):
        """Plot volume with filtered signal."""
        if 'volume_raw' not in indicators.columns:
            ax.text(0.5, 0.5, 'No volume data', ha='center', va='center')
            return

        ax.bar(indicators.index, indicators['volume_raw'],
              label='Volume Raw', alpha=0.4, color='gray')
        ax.plot(indicators.index, indicators['volume_filtered'],
               label='Volume Filtered', linewidth=2, color='blue')

        if 'volume_filtered_ma' in indicators.columns:
            ax.plot(indicators.index, indicators['volume_filtered_ma'],
                   label='Volume MA', linewidth=1, color='red', linestyle='--')

        ax.set_title('Volume (Raw vs Filtered)', fontweight='bold')
        ax.set_ylabel('Volume')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)

    def _plot_stochastic(self, ax, indicators: pd.DataFrame):
        """Plot Stochastic with filtered signals."""
        if 'stoch_k_filtered' not in indicators.columns:
            ax.text(0.5, 0.5, 'No Stochastic data', ha='center', va='center')
            return

        ax.plot(indicators.index, indicators['stoch_k_filtered'],
               label='%K Filtered', linewidth=2, color='blue')
        ax.plot(indicators.index, indicators['stoch_d_filtered'],
               label='%D Filtered', linewidth=2, color='red')

        ax.axhline(y=80, color='r', linestyle='--', alpha=0.5, label='Overbought')
        ax.axhline(y=20, color='g', linestyle='--', alpha=0.5, label='Oversold')

        ax.set_title('Stochastic (Filtered)', fontweight='bold')
        ax.set_ylabel('Stochastic')
        ax.set_ylim([0, 100])
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)

    def _plot_correlation_heatmap(self, ax, correlation_matrix: pd.DataFrame):
        """Plot correlation heatmap."""
        if correlation_matrix is None or correlation_matrix.empty:
            ax.text(0.5, 0.5, 'No correlation data', ha='center', va='center')
            return

        # Select subset if too large
        if len(correlation_matrix) > 15:
            # Take most important indicators
            subset = correlation_matrix.iloc[:15, :15]
        else:
            subset = correlation_matrix

        sns.heatmap(subset, annot=False, cmap='RdYlGn', center=0,
                   square=True, ax=ax, cbar_kws={'label': 'Correlation'})

        ax.set_title('Indicator Correlation Heatmap (Filtered Signals)', fontweight='bold')

    def _plot_equity_curve(self, ax, backtest_results: pd.DataFrame):
        """Plot equity curve with drawdown."""
        if 'equity' not in backtest_results.columns:
            ax.text(0.5, 0.5, 'No equity data', ha='center', va='center')
            return

        # Equity curve
        ax2 = ax.twinx()

        ax.plot(backtest_results.index, backtest_results['equity'],
               label='Equity Curve', linewidth=2, color='green')
        ax.fill_between(backtest_results.index, backtest_results['equity'],
                        alpha=0.3, color='green')

        # Drawdown
        cummax = backtest_results['equity'].cummax()
        drawdown = (backtest_results['equity'] - cummax) / cummax * 100

        ax2.fill_between(backtest_results.index, 0, drawdown,
                        label='Drawdown', alpha=0.3, color='red')
        ax2.plot(backtest_results.index, drawdown,
                linewidth=1, color='red', alpha=0.5)

        ax.set_title('Equity Curve and Drawdown', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Equity ($)', color='green')
        ax2.set_ylabel('Drawdown (%)', color='red')
        ax.legend(loc='upper left', fontsize=8)
        ax2.legend(loc='lower left', fontsize=8)
        ax.grid(True, alpha=0.3)

    def _plot_signal_strength(self, ax, trade_signals: pd.DataFrame):
        """Plot signal strength and confidence over time."""
        if 'composite_signal' not in trade_signals.columns:
            ax.text(0.5, 0.5, 'No signal data', ha='center', va='center')
            return

        # Clean data - remove NaN and inf
        clean_signals = trade_signals.copy()
        if 'composite_signal' in clean_signals.columns:
            clean_signals['composite_signal'] = clean_signals['composite_signal'].replace([np.inf, -np.inf], np.nan).fillna(0)
        if 'confidence' in clean_signals.columns:
            clean_signals['confidence'] = clean_signals['confidence'].replace([np.inf, -np.inf], np.nan).fillna(50)

        # Get signals from parent (need to pass this separately)
        # For now, just plot what we have
        ax2 = ax.twinx()

        # Composite signal
        ax.plot(clean_signals.index, clean_signals.get('composite_signal', 0),
               label='Composite Signal', linewidth=2, color='blue')
        ax.fill_between(clean_signals.index,
                       0,
                       clean_signals.get('composite_signal', 0),
                       alpha=0.3, color='blue')

        # Confidence if available
        if 'confidence' in clean_signals.columns:
            ax2.plot(clean_signals.index, clean_signals['confidence'],
                    label='Confidence', linewidth=1, color='orange', alpha=0.7)

        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        ax.axhline(y=0.5, color='g', linestyle='--', alpha=0.3, label='Entry Threshold')
        ax.axhline(y=-0.5, color='r', linestyle='--', alpha=0.3)

        ax.set_title('Signal Strength and Confidence', fontweight='bold')
        ax.set_xlabel('Date')
        ax.set_ylabel('Signal (-1 to 1)', color='blue')
        ax2.set_ylabel('Confidence (0-100)', color='orange')
        ax.legend(loc='upper left', fontsize=8)
        if 'confidence' in clean_signals.columns:
            ax2.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)

    def plot_performance_summary(self,
                                backtest_results: pd.DataFrame,
                                metrics: Dict,
                                save_path: str = None):
        """
        Create a focused performance summary plot.

        Args:
            backtest_results: Backtest results
            metrics: Performance metrics dictionary
            save_path: Optional save path
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. Equity curve
        ax1 = axes[0, 0]
        ax1.plot(backtest_results.index, backtest_results['equity'],
                linewidth=2, color='green')
        ax1.set_title('Equity Curve', fontweight='bold')
        ax1.set_ylabel('Equity ($)')
        ax1.grid(True, alpha=0.3)

        # 2. Drawdown
        ax2 = axes[0, 1]
        cummax = backtest_results['equity'].cummax()
        drawdown = (backtest_results['equity'] - cummax) / cummax * 100
        ax2.fill_between(backtest_results.index, 0, drawdown, color='red', alpha=0.5)
        ax2.set_title('Drawdown', fontweight='bold')
        ax2.set_ylabel('Drawdown (%)')
        ax2.grid(True, alpha=0.3)

        # 3. Returns distribution
        ax3 = axes[1, 0]
        returns = backtest_results['returns'].dropna()
        ax3.hist(returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
        ax3.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax3.set_title('Returns Distribution', fontweight='bold')
        ax3.set_xlabel('Returns')
        ax3.set_ylabel('Frequency')
        ax3.grid(True, alpha=0.3)

        # 4. Metrics table
        ax4 = axes[1, 1]
        ax4.axis('off')

        metrics_text = f"""
        PERFORMANCE METRICS
        {'='*40}
        Total Return:       {metrics['total_return_pct']:.2f}%
        Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}
        Max Drawdown:       {metrics['max_drawdown_pct']:.2f}%

        Win Rate:           {metrics['win_rate_pct']:.2f}%
        Profit Factor:      {metrics['profit_factor']:.2f}
        Num Trades:         {metrics['num_trades']}

        Annualized Return:  {metrics['annualized_return_pct']:.2f}%
        Volatility:         {metrics['volatility_pct']:.2f}%
        """

        ax4.text(0.1, 0.5, metrics_text, fontsize=11, family='monospace',
                verticalalignment='center')

        plt.suptitle('Performance Summary', fontsize=16, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_indicator_comparison(self,
                                 indicators: pd.DataFrame,
                                 indicator_name: str,
                                 save_path: str = None):
        """
        Compare raw vs filtered for a specific indicator.

        Args:
            indicators: Indicators DataFrame
            indicator_name: Base name (e.g., 'rsi', 'macd')
            save_path: Optional save path
        """
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))

        raw_col = f'{indicator_name}_raw'
        filtered_col = f'{indicator_name}_filtered'

        if raw_col not in indicators.columns or filtered_col not in indicators.columns:
            print(f"Columns {raw_col} or {filtered_col} not found")
            return None

        # 1. Raw vs Filtered
        ax1 = axes[0]
        ax1.plot(indicators.index, indicators[raw_col],
                label='Raw', alpha=0.5, linewidth=1)
        ax1.plot(indicators.index, indicators[filtered_col],
                label='Filtered', linewidth=2)
        ax1.set_title(f'{indicator_name.upper()} - Raw vs Filtered', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Difference
        ax2 = axes[1]
        diff = indicators[raw_col] - indicators[filtered_col]
        ax2.plot(indicators.index, diff, color='red', linewidth=1)
        ax2.fill_between(indicators.index, 0, diff, alpha=0.3, color='red')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax2.set_title('Noise Removed (Raw - Filtered)', fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 3. Rolling correlation
        ax3 = axes[2]
        rolling_corr = indicators[raw_col].rolling(window=20).corr(indicators[filtered_col])
        ax3.plot(indicators.index, rolling_corr, linewidth=2, color='green')
        ax3.axhline(y=0.7, color='orange', linestyle='--', label='Threshold')
        ax3.set_title('Rolling Correlation (Raw vs Filtered)', fontweight='bold')
        ax3.set_ylabel('Correlation')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig
