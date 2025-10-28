"""
Main Fourier Trading Strategy

This is the main orchestrator that combines all components to create
a complete trading strategy with Fourier Transform filtering.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
import warnings

from .fourier_processor import FourierTransformProcessor
from .multi_timeframe_ema import MultiTimeframeEMA
from .fourier_indicators import FourierIndicators
from .correlation_analyzer import CorrelationAnalyzer
from .signal_generator import SignalGenerator
from .backtester import Backtester
from .visualizer import StrategyVisualizer

warnings.filterwarnings('ignore')


class FourierTradingStrategy:
    """
    Complete Fourier-based trading strategy.

    Combines:
    - Fourier Transform filtering
    - Multi-timeframe EMA analysis
    - Technical indicators with Fourier
    - Cross-indicator correlation
    - Signal generation
    - Backtesting
    - Visualization
    """

    def __init__(self,
                 # Fourier parameters
                 n_harmonics: int = 5,
                 noise_threshold: float = 0.3,

                 # EMA parameters
                 base_ema_period: int = 28,
                 ema_timeframe_multipliers: list = None,

                 # Indicator parameters
                 rsi_period: int = 14,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 atr_period: int = 14,

                 # Correlation parameters
                 correlation_window: int = 20,
                 correlation_threshold: float = 0.7,

                 # Signal parameters
                 min_signal_strength: float = 0.5,
                 signal_weights: Dict[str, float] = None,
                 max_holding_periods: int = 336,  # ~2 weeks for hourly data

                 # Backtest parameters
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,
                 slippage: float = 0.0005):
        """
        Initialize Fourier Trading Strategy.

        Args:
            n_harmonics: Number of harmonics for Fourier filtering
            noise_threshold: Noise threshold for filtering
            base_ema_period: Base EMA period
            ema_timeframe_multipliers: EMA timeframe multipliers
            rsi_period: RSI period
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            atr_period: ATR period
            correlation_window: Correlation window
            correlation_threshold: Correlation threshold
            min_signal_strength: Minimum signal strength to trade
            signal_weights: Custom signal weights
            initial_capital: Initial capital for backtesting
            commission: Commission rate
            slippage: Slippage rate
        """
        # Store parameters
        self.params = {
            'n_harmonics': n_harmonics,
            'noise_threshold': noise_threshold,
            'base_ema_period': base_ema_period,
            'ema_timeframe_multipliers': ema_timeframe_multipliers or [1, 2, 4, 8],
            'rsi_period': rsi_period,
            'macd_fast': macd_fast,
            'macd_slow': macd_slow,
            'macd_signal': macd_signal,
            'atr_period': atr_period,
            'correlation_window': correlation_window,
            'correlation_threshold': correlation_threshold,
            'min_signal_strength': min_signal_strength,
            'signal_weights': signal_weights,
            'max_holding_periods': max_holding_periods,
            'initial_capital': initial_capital,
            'commission': commission,
            'slippage': slippage
        }

        # Initialize components
        self.fourier_processor = FourierTransformProcessor(
            n_harmonics=n_harmonics,
            noise_threshold=noise_threshold
        )

        self.ema_analyzer = MultiTimeframeEMA(
            base_period=base_ema_period,
            timeframe_multipliers=ema_timeframe_multipliers or [1, 2, 4, 8],
            n_harmonics=n_harmonics,
            noise_threshold=noise_threshold
        )

        self.indicator_processor = FourierIndicators(
            rsi_period=rsi_period,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            atr_period=atr_period,
            n_harmonics=n_harmonics,
            noise_threshold=noise_threshold
        )

        self.correlation_analyzer = CorrelationAnalyzer(
            correlation_window=correlation_window,
            correlation_threshold=correlation_threshold
        )

        self.signal_generator = SignalGenerator(
            correlation_threshold=correlation_threshold,
            min_signal_strength=min_signal_strength,
            signal_weights=signal_weights,
            max_holding_periods=max_holding_periods
        )

        self.backtester = Backtester(
            initial_capital=initial_capital,
            commission=commission,
            slippage=slippage
        )

        self.visualizer = StrategyVisualizer()

        # Storage for results
        self.results = {}

    def run(self,
            df: pd.DataFrame,
            price_col: str = 'close',
            open_col: str = 'open',
            high_col: str = 'high',
            low_col: str = 'low',
            volume_col: str = 'volume',
            run_backtest: bool = True,
            verbose: bool = True) -> Dict:
        """
        Run the complete strategy pipeline.

        Args:
            df: OHLCV DataFrame
            price_col: Column name for close price
            open_col: Column name for open price
            high_col: Column name for high price
            low_col: Column name for low price
            volume_col: Column name for volume
            run_backtest: Whether to run backtest
            verbose: Print progress messages

        Returns:
            Dictionary with all results
        """
        if verbose:
            print("=" * 70)
            print("FOURIER TRADING STRATEGY - PROCESSING")
            print("=" * 70)

        # Extract OHLCV
        close = df[price_col]
        open_ = df[open_col]
        high = df[high_col]
        low = df[low_col]
        volume = df[volume_col]

        # Step 1: Fourier filter price
        if verbose:
            print("\n[1/7] Applying Fourier Transform to price...")

        price_result = self.fourier_processor.process_signal(close)
        price_filtered = pd.Series(price_result['filtered'], index=close.index)

        # Step 2: Multi-timeframe EMA analysis
        if verbose:
            print("[2/7] Analyzing Multi-Timeframe EMAs with Fourier...")

        ema_results = self.ema_analyzer.process(close)

        # Step 3: Process all indicators with Fourier
        if verbose:
            print("[3/7] Processing Technical Indicators with Fourier...")

        indicators = self.indicator_processor.process_all_indicators(
            open_, high, low, close, volume
        )

        # Get individual indicator signals
        indicator_signals = self.indicator_processor.get_indicator_signals(indicators)

        # Step 4: Correlation analysis
        if verbose:
            print("[4/7] Analyzing Cross-Indicator Correlations...")

        correlation_analysis = self.correlation_analyzer.analyze_indicator_relationships(
            price_filtered,
            indicators,
            ema_results['filtered_emas']
        )

        correlation_score = pd.Series(
            self.correlation_analyzer.get_correlation_score(price_filtered, indicators),
            index=close.index
        )

        # Step 5: Generate signals
        if verbose:
            print("[5/7] Generating Trading Signals...")

        signal_results = self.signal_generator.process(
            close,
            price_filtered,
            ema_results,
            indicators,
            indicator_signals,
            correlation_score,
            indicators.get('atr_filtered', None)
        )

        # Step 6: Backtest (optional)
        backtest_results = None
        metrics = None
        trade_log = None

        if run_backtest:
            if verbose:
                print("[6/7] Running Backtest...")

            backtest_output = self.backtester.run_backtest(
                close,
                signal_results['trades'],
                position_size=0.25,  # 25% of capital per trade (conservative)
                verbose=verbose
            )

            backtest_results = backtest_output['backtest_results']
            metrics = backtest_output['metrics']
            trade_log = backtest_output['trade_log']

        # Step 7: Prepare output DataFrame
        if verbose:
            print("[7/7] Preparing Output DataFrame...")

        output_df = self._create_output_dataframe(
            df,
            price_filtered,
            ema_results,
            indicators,
            indicator_signals,
            signal_results,
            correlation_score,
            backtest_results
        )

        # Store results
        self.results = {
            'output_df': output_df,
            'price_filtered': price_filtered,
            'ema_results': ema_results,
            'indicators': indicators,
            'indicator_signals': indicator_signals,
            'correlation_analysis': correlation_analysis,
            'signal_results': signal_results,
            'backtest_results': backtest_results,
            'metrics': metrics,
            'trade_log': trade_log,
            'parameters': self.params
        }

        if verbose:
            print("\n" + "=" * 70)
            print("PROCESSING COMPLETE")
            print("=" * 70)

        return self.results

    def _create_output_dataframe(self,
                                 df: pd.DataFrame,
                                 price_filtered: pd.Series,
                                 ema_results: Dict,
                                 indicators: pd.DataFrame,
                                 indicator_signals: pd.DataFrame,
                                 signal_results: Dict,
                                 correlation_score: pd.Series,
                                 backtest_results: Optional[pd.DataFrame]) -> pd.DataFrame:
        """Create comprehensive output DataFrame."""
        output = df.copy()

        # Add filtered price
        output['price_filtered'] = price_filtered

        # Add EMA data
        for col in ema_results['emas'].columns:
            output[col] = ema_results['emas'][col]

        for col in ema_results['filtered_emas'].columns:
            output[col] = ema_results['filtered_emas'][col]

        # Add EMA metrics
        for col in ema_results['alignment'].columns:
            output[col] = ema_results['alignment'][col]

        # Add key indicators (filtered versions)
        key_indicators = [
            'rsi_raw', 'rsi_filtered',
            'macd_filtered', 'signal_filtered', 'histogram_filtered',
            'volume_filtered', 'atr_filtered',
            'stoch_k_filtered', 'stoch_d_filtered'
        ]

        for col in key_indicators:
            if col in indicators.columns:
                output[col] = indicators[col]

        # Add indicator signals
        for col in indicator_signals.columns:
            output[col] = indicator_signals[col]

        # Add composite signals
        output['composite_signal'] = signal_results['signals']['composite_signal']
        output['signal_confidence'] = signal_results['confidence']

        # Add trade signals
        output['position'] = signal_results['trades']['position']
        output['trade_signal'] = signal_results['trades']['trade_signal']

        # Add correlation score
        output['correlation_score'] = correlation_score

        # Add backtest results if available
        if backtest_results is not None:
            output['equity'] = backtest_results['equity']
            output['returns'] = backtest_results['returns']

        return output

    def visualize(self,
                 plot_type: str = 'comprehensive',
                 save_path: str = None):
        """
        Create visualizations.

        Args:
            plot_type: Type of plot ('comprehensive', 'performance', or 'indicator')
            save_path: Path to save figure

        Returns:
            matplotlib Figure
        """
        if not self.results:
            raise ValueError("No results available. Run strategy first with .run()")

        if plot_type == 'comprehensive':
            fig = self.visualizer.plot_comprehensive_analysis(
                self.results['output_df']['close'],
                self.results['price_filtered'],
                self.results['ema_results'],
                self.results['indicators'],
                self.results['signal_results']['trades'],
                self.results['backtest_results'],
                self.results['correlation_analysis']['correlation_matrix'],
                self.results['trade_log'],
                save_path=save_path
            )

        elif plot_type == 'performance':
            if self.results['backtest_results'] is None:
                raise ValueError("No backtest results available")

            fig = self.visualizer.plot_performance_summary(
                self.results['backtest_results'],
                self.results['metrics'],
                save_path=save_path
            )

        else:
            raise ValueError(f"Unknown plot type: {plot_type}")

        return fig

    def get_current_signal(self) -> Dict:
        """
        Get the most recent signal.

        Returns:
            Dictionary with current signal information
        """
        if not self.results:
            raise ValueError("No results available. Run strategy first with .run()")

        latest_idx = -1

        signal_data = self.results['signal_results']['signals'].iloc[latest_idx]
        trade_data = self.results['signal_results']['trades'].iloc[latest_idx]

        return {
            'composite_signal': signal_data['composite_signal'],
            'confidence': signal_data.get('confidence', 0),
            'position': trade_data['position'],
            'trade_signal': trade_data['trade_signal'],
            'signal_reason': trade_data.get('signal_reason', ''),
            'price': self.results['output_df']['close'].iloc[latest_idx],
            'price_filtered': self.results['price_filtered'].iloc[latest_idx],
            'correlation_score': self.results['output_df']['correlation_score'].iloc[latest_idx],
            'timestamp': self.results['output_df'].index[latest_idx]
        }

    def export_results(self, filepath: str, format: str = 'csv'):
        """
        Export results to file.

        Args:
            filepath: Output file path
            format: Export format ('csv', 'excel', 'json')
        """
        if not self.results:
            raise ValueError("No results available. Run strategy first with .run()")

        output_df = self.results['output_df']

        if format == 'csv':
            output_df.to_csv(filepath)
        elif format == 'excel':
            output_df.to_excel(filepath)
        elif format == 'json':
            output_df.to_json(filepath, orient='index', indent=2)
        else:
            raise ValueError(f"Unknown format: {format}")

        print(f"Results exported to {filepath}")

    def get_summary(self) -> str:
        """Get a text summary of strategy results."""
        if not self.results or self.results['metrics'] is None:
            return "No results available. Run strategy with run_backtest=True first."

        metrics = self.results['metrics']

        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║         FOURIER TRADING STRATEGY - SUMMARY                   ║
╚══════════════════════════════════════════════════════════════╝

PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Harmonics:              {self.params['n_harmonics']}
Noise Threshold:        {self.params['noise_threshold']}
Base EMA Period:        {self.params['base_ema_period']}
Correlation Threshold:  {self.params['correlation_threshold']}
Min Signal Strength:    {self.params['min_signal_strength']}

PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Return:          {metrics['total_return_pct']:.2f}%
Sharpe Ratio:          {metrics['sharpe_ratio']:.2f}
Max Drawdown:          {metrics['max_drawdown_pct']:.2f}%
Win Rate:              {metrics['win_rate_pct']:.2f}%
Profit Factor:         {metrics['profit_factor']:.2f}
Number of Trades:      {metrics['num_trades']}

Current Signal:        {self.get_current_signal()['composite_signal']:.2f}
Current Confidence:    {self.get_current_signal()['confidence']:.1f}%
"""
        return summary
