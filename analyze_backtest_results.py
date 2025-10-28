#!/usr/bin/env python3
"""
Comprehensive Backtest Results Analysis and Visualization
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('.')))
sys.path.insert(0, str(Path('.') / 'src'))
sys.path.insert(0, str(Path('.') / 'fourier_strategy'))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Set style
plt.style.use('dark_background')
sns.set_palette("husl")

class BacktestAnalyzer:
    """Analyze and visualize backtest results"""

    def __init__(self):
        self.results = []
        self.trades_data = {}

    def run_backtest_and_analyze(self):
        """Run the complete backtest and analyze results"""
        print("🚀 Starting Comprehensive Backtest Analysis")
        print("="*60)

        # Import and run the backtest
        try:
            from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter
            from src.live.fibonacci_signal_generator import FibonacciSignalGenerator
            from src.live.adaptive_kalman_filter import AdaptiveKalmanFilter
            from src.live.signal_fusion_engine import SignalFusionEngine, Signal, SignalType
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Please ensure all required modules are available")
            return

        # Test configurations
        iterations = {
            1: {
                "name": "Iteration 1 - Conservative",
                "compression": 85,
                "alignment": 85,
                "confluence": 60,
                "min_confidence": 0.65,
                "min_coherence": 0.6,
                "expected_return": "3.5-4.5%",
                "expected_win_rate": "82-85%"
            },
            2: {
                "name": "Iteration 2 - Moderate",
                "compression": 82,
                "alignment": 83,
                "confluence": 58,
                "min_confidence": 0.6,
                "min_coherence": 0.55,
                "expected_return": "5-6%",
                "expected_win_rate": "78-82%"
            },
            3: {
                "name": "Iteration 3 - Aggressive",
                "compression": 80,
                "alignment": 80,
                "confluence": 55,
                "min_confidence": 0.55,
                "min_coherence": 0.5,
                "expected_return": "6.5-8%",
                "expected_win_rate": "75-80%"
            }
        }

        # Trading parameters
        trading_params = {
            'leverage': 27,
            'position_size_pct': 9.0,
            'base_sl_pct': 0.54,
            'min_rr_ratio': 1.5,
            'max_rr_ratio': 4.0,
            'max_holding_periods': 27,
            'min_holding_periods': 3
        }

        # Fetch data
        print("📊 Fetching market data...")
        adapter = HyperliquidDataAdapter()
        df = adapter.fetch_ohlcv(interval='5m', days_back=17)
        print(f"✅ Fetched {len(df)} candles")

        # Run each iteration
        for iter_num, config in iterations.items():
            print(f"\n🧪 Running {config['name']}")
            print(f"   Parameters: {config['compression']}/{config['alignment']}/{config['confluence']}")

            result = self._run_single_iteration(df, config, trading_params, iter_num)
            self.results.append(result)
            print(f"   ✅ Completed: {result['num_trades']} trades, {result['return_17d']:.2f}% return")

        # Generate analysis
        self._generate_comprehensive_analysis()

    def _run_single_iteration(self, df: pd.DataFrame, config: Dict, trading_params: Dict, iter_num: int) -> Dict:
        """Run a single backtest iteration"""

        # Initialize components
        fib_generator = FibonacciSignalGenerator(
            compression_threshold=config['compression'],
            alignment_threshold=config['alignment'],
            confluence_threshold=config['confluence'],
            use_volume_fft=False,
            use_fib_levels=False
        )

        kalman_filter = AdaptiveKalmanFilter(dt=5.0)
        signal_fusion = SignalFusionEngine(
            min_confidence=config['min_confidence'],
            min_coherence=config['min_coherence']
        )

        # Trading state
        capital = 1000.0
        position = 0
        entry_price = 0
        entry_time = None
        tp_price = 0
        sl_price = 0
        trades = []
        equity_curve = []

        # Run through data
        for i in range(200, len(df)):
            current_time = df.index[i]
            current_price = df['close'].iloc[i]

            # Get data window for Fibonacci analysis
            df_window = df.iloc[max(0, i-300):i+1].copy()

            # Check exit conditions first
            if position != 0:
                holding_periods = i - df.index.get_loc(entry_time)

                if holding_periods > 0:
                    should_exit = False
                    exit_reason = None

                    # Check TP/SL
                    if position == 1:  # Long
                        if df['high'].iloc[i] >= tp_price:
                            should_exit = True
                            exit_reason = 'TP'
                            current_price = tp_price
                        elif df['low'].iloc[i] <= sl_price:
                            should_exit = True
                            exit_reason = 'SL'
                            current_price = sl_price
                    else:  # Short
                        if df['low'].iloc[i] <= tp_price:
                            should_exit = True
                            exit_reason = 'TP'
                            current_price = tp_price
                        elif df['high'].iloc[i] >= sl_price:
                            should_exit = True
                            exit_reason = 'SL'
                            current_price = sl_price

                    # Check max holding period
                    if not should_exit and holding_periods >= trading_params['max_holding_periods']:
                        should_exit = True
                        exit_reason = 'MAX_HOLD'

                    # Execute exit
                    if should_exit:
                        if position == 1:
                            pnl_pct = (current_price - entry_price) / entry_price * 100
                        else:
                            pnl_pct = (entry_price - current_price) / entry_price * 100

                        # Apply leverage
                        pnl_pct *= trading_params['leverage']
                        pnl_usd = capital * (trading_params['position_size_pct'] / 100) * (pnl_pct / 100)
                        capital += pnl_usd

                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': current_time,
                            'direction': 'LONG' if position == 1 else 'SHORT',
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'pnl_pct': pnl_pct,
                            'exit_reason': exit_reason,
                            'holding_periods': holding_periods
                        })

                        position = 0

            # Check entry conditions if flat
            if position == 0:
                # Generate Fibonacci signal
                fib_signal = fib_generator.generate_signal(df_window)

                if fib_signal is None:
                    continue

                # Update Kalman filter
                kalman_state = kalman_filter.update(current_price)
                velocity = kalman_filter.get_velocity_estimate()
                trend_direction = kalman_filter.get_trend_direction()

                # Create signal objects
                signals_to_fuse = []

                # Fibonacci signal
                if fib_signal['signal'] == 'LONG':
                    fib_signal_type = SignalType.LONG
                elif fib_signal['signal'] == 'SHORT':
                    fib_signal_type = SignalType.SHORT
                else:
                    fib_signal_type = SignalType.NEUTRAL

                signals_to_fuse.append(Signal(
                    signal_type=fib_signal_type,
                    strength=fib_signal['strength'],
                    confidence=fib_signal['confidence'],
                    timeframe='5m',
                    source='fibonacci_fft',
                    timestamp=i
                ))

                # Kalman signal
                if trend_direction == 1:
                    kalman_signal_type = SignalType.LONG
                elif trend_direction == -1:
                    kalman_signal_type = SignalType.SHORT
                else:
                    kalman_signal_type = SignalType.NEUTRAL

                if kalman_signal_type != SignalType.NEUTRAL:
                    signals_to_fuse.append(Signal(
                        signal_type=kalman_signal_type,
                        strength=min(abs(velocity) * 10, 1.0),
                        confidence=kalman_state.confidence,
                        timeframe='5m',
                        source='kalman_filter',
                        timestamp=i
                    ))

                # Fuse signals
                fused = signal_fusion.fuse_signals(signals_to_fuse, current_regime='neutral')

                if fused and fused.confidence >= config['min_confidence'] and fused.coherence >= config['min_coherence']:
                    # Enter trade
                    if fused.signal_type == SignalType.LONG:
                        position = 1
                        entry_price = current_price
                        entry_time = current_time

                        # Calculate adaptive TP/SL
                        signal_quality = (fib_signal['compression'] + fib_signal['alignment']) / 2

                        if signal_quality >= 90:
                            rr_ratio = 4.0
                        elif signal_quality >= 85:
                            rr_ratio = 3.0
                        elif signal_quality >= 80:
                            rr_ratio = 2.0
                        else:
                            rr_ratio = 1.5

                        sl_pct = trading_params['base_sl_pct'] / 100
                        tp_pct = sl_pct * rr_ratio

                        sl_price = entry_price * (1 - sl_pct)
                        tp_price = entry_price * (1 + tp_pct)

                    elif fused.signal_type == SignalType.SHORT:
                        position = -1
                        entry_price = current_price
                        entry_time = current_time

                        # Calculate adaptive TP/SL
                        signal_quality = (fib_signal['compression'] + fib_signal['alignment']) / 2

                        if signal_quality >= 90:
                            rr_ratio = 4.0
                        elif signal_quality >= 85:
                            rr_ratio = 3.0
                        elif signal_quality >= 80:
                            rr_ratio = 2.0
                        else:
                            rr_ratio = 1.5

                        sl_pct = trading_params['base_sl_pct'] / 100
                        tp_pct = sl_pct * rr_ratio

                        sl_price = entry_price * (1 + sl_pct)
                        tp_price = entry_price * (1 - tp_pct)

            # Record equity
            equity_curve.append({
                'time': current_time,
                'capital': capital,
                'price': current_price
            })

        # Calculate metrics
        if len(trades) == 0:
            return {
                'iteration': config['name'],
                'return_17d': 0.0,
                'win_rate': 0.0,
                'sharpe': 0.0,
                'num_trades': 0,
                'trades_per_day': 0.0,
                'trades': [],
                'equity_curve': equity_curve
            }

        returns = [t['pnl_pct'] for t in trades]
        wins = [r for r in returns if r > 0]

        total_return = ((capital - 1000) / 1000) * 100
        win_rate = (len(wins) / len(trades)) * 100

        if len(returns) > 1 and np.std(returns) > 0:
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        else:
            sharpe = 0.0

        days = (df.index[-1] - df.index[200]).total_seconds() / 86400
        trades_per_day = len(trades) / days if days > 0 else 0

        # Store detailed trade data
        self.trades_data[iter_num] = {
            'trades': trades,
            'equity_curve': equity_curve,
            'config': config
        }

        return {
            'iteration': config['name'],
            'return_17d': total_return,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'num_trades': len(trades),
            'trades_per_day': trades_per_day,
            'trades': trades,
            'equity_curve': equity_curve
        }

    def _generate_comprehensive_analysis(self):
        """Generate comprehensive analysis and charts"""
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE BACKTEST ANALYSIS")
        print("="*60)

        # Create output directory
        output_dir = Path('backtest_analysis')
        output_dir.mkdir(exist_ok=True)

        # 1. Summary Comparison Table
        self._create_summary_table()

        # 2. Performance Charts
        self._create_performance_charts(output_dir)

        # 3. Trade Analysis
        self._create_trade_analysis(output_dir)

        # 4. Risk Analysis
        self._create_risk_analysis(output_dir)

        # 5. Save results
        self._save_results(output_dir)

        print(f"\n✅ Analysis complete! Charts saved to {output_dir}/")

    def _create_summary_table(self):
        """Create summary comparison table"""
        print("\n📈 PERFORMANCE SUMMARY")
        print("-" * 80)

        print(f"{'Iteration':<25} {'Return':<10} {'Win Rate':<12} {'Sharpe':<8} {'Trades':<8} {'Trades/Day':<12}")
        print("-" * 80)

        for i, result in enumerate(self.results, 1):
            config = self.trades_data[i]['config']
            print(f"{result['iteration']:<25} {result['return_17d']:>8.2f}%  {result['win_rate']:>10.1f}%  {result['sharpe']:>6.2f}  {result['num_trades']:>6}  {result['trades_per_day']:>10.2f}")
            print(f"{'  Expected: ' + config['expected_return'] + ', ' + config['expected_win_rate']:<58}")

        print("-" * 80)

    def _create_performance_charts(self, output_dir: Path):
        """Create performance visualization charts"""

        # 1. Equity Curves
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Backtest Performance Analysis', fontsize=16, fontweight='bold')

        # Equity curves comparison
        ax1 = axes[0, 0]
        for i, result in enumerate(self.results, 1):
            if result['equity_curve']:
                equity_df = pd.DataFrame(result['equity_curve'])
                ax1.plot(equity_df['time'], equity_df['capital'],
                        label=f"Iteration {i}", linewidth=2)

        ax1.set_title('Equity Curves Comparison', fontweight='bold')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Capital ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))

        # 2. Returns Comparison
        ax2 = axes[0, 1]
        iterations = [f"Iteration {i}" for i in range(1, len(self.results)+1)]
        returns = [r['return_17d'] for r in self.results]
        expected_returns = [3.5, 5.5, 7.25]  # Midpoint of expected ranges

        x = np.arange(len(iterations))
        width = 0.35

        bars1 = ax2.bar(x - width/2, returns, width, label='Actual', color='#00ff88', alpha=0.8)
        bars2 = ax2.bar(x + width/2, expected_returns, width, label='Expected', color='#ff6b6b', alpha=0.8)

        ax2.set_title('Returns vs Expected', fontweight='bold')
        ax2.set_ylabel('Return (%)')
        ax2.set_xticks(x)
        ax2.set_xticklabels(iterations)
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}%', ha='center', va='bottom')

        # 3. Win Rates Comparison
        ax3 = axes[1, 0]
        win_rates = [r['win_rate'] for r in self.results]
        expected_win_rates = [83.5, 80, 77.5]  # Midpoint of expected ranges

        bars1 = ax3.bar(x - width/2, win_rates, width, label='Actual', color='#00ff88', alpha=0.8)
        bars2 = ax3.bar(x + width/2, expected_win_rates, width, label='Expected', color='#ff6b6b', alpha=0.8)

        ax3.set_title('Win Rates vs Expected', fontweight='bold')
        ax3.set_ylabel('Win Rate (%)')
        ax3.set_xticks(x)
        ax3.set_xticklabels(iterations)
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}%', ha='center', va='bottom')

        # 4. Trade Count Analysis
        ax4 = axes[1, 1]
        trade_counts = [r['num_trades'] for r in self.results]
        colors = ['#4ecdc4', '#f7b731', '#5f27cd']

        bars = ax4.bar(iterations, trade_counts, color=colors, alpha=0.8)
        ax4.set_title('Number of Trades per Iteration', fontweight='bold')
        ax4.set_ylabel('Number of Trades')
        ax4.grid(True, alpha=0.3)

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        plt.savefig(output_dir / 'performance_overview.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _create_trade_analysis(self, output_dir: Path):
        """Create detailed trade analysis charts"""

        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Trade Analysis Details', fontsize=16, fontweight='bold')

        for i, (iter_num, data) in enumerate(self.trades_data.items()):
            trades = data['trades']
            if not trades:
                continue

            trades_df = pd.DataFrame(trades)

            # 1. PnL Distribution
            ax1 = axes[0, 0] if i == 1 else axes[0, 1] if i == 2 else axes[0, 2]

            wins = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct']
            losses = trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct']

            ax1.hist(wins, bins=20, alpha=0.7, color='green', label='Wins')
            ax1.hist(losses, bins=20, alpha=0.7, color='red', label='Losses')
            ax1.set_title(f'Iteration {iter_num} PnL Distribution')
            ax1.set_xlabel('PnL (%)')
            ax1.set_ylabel('Frequency')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. Exit Reasons
            ax2 = axes[1, 0] if i == 1 else axes[1, 1] if i == 2 else axes[1, 2]

            exit_reasons = trades_df['exit_reason'].value_counts()
            colors = ['#4ecdc4', '#f7b731', '#5f27cd']
            ax2.pie(exit_reasons.values, labels=exit_reasons.index, autopct='%1.1f%%',
                   colors=colors[:len(exit_reasons)])
            ax2.set_title(f'Iteration {iter_num} Exit Reasons')

        plt.tight_layout()
        plt.savefig(output_dir / 'trade_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _create_risk_analysis(self, output_dir: Path):
        """Create risk analysis charts"""

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Risk Analysis', fontsize=16, fontweight='bold')

        # 1. Sharpe Ratios
        ax1 = axes[0, 0]
        sharpe_ratios = [r['sharpe'] for r in self.results]
        iterations = [f"Iteration {i}" for i in range(1, len(self.results)+1)]
        colors = ['#4ecdc4', '#f7b731', '#5f27cd']

        bars = ax1.bar(iterations, sharpe_ratios, color=colors, alpha=0.8)
        ax1.set_title('Sharpe Ratios by Iteration')
        ax1.set_ylabel('Sharpe Ratio')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=1.0, color='red', linestyle='--', alpha=0.7, label='Target (1.0)')
        ax1.legend()

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    f'{height:.2f}', ha='center', va='bottom', fontweight='bold')

        # 2. Trade Frequency
        ax2 = axes[0, 1]
        trades_per_day = [r['trades_per_day'] for r in self.results]

        bars = ax2.bar(iterations, trades_per_day, color=colors, alpha=0.8)
        ax2.set_title('Trade Frequency (Trades per Day)')
        ax2.set_ylabel('Trades per Day')
        ax2.grid(True, alpha=0.3)

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{height:.2f}', ha='center', va='bottom', fontweight='bold')

        # 3. Maximum Drawdown Analysis
        ax3 = axes[1, 0]
        for i, result in enumerate(self.results, 1):
            if result['equity_curve']:
                equity_df = pd.DataFrame(result['equity_curve'])
                equity_df['drawdown'] = (equity_df['capital'].cummax() - equity_df['capital']) / equity_df['capital'].cummax() * 100
                ax3.plot(equity_df['time'], equity_df['drawdown'],
                        label=f"Iteration {i}", linewidth=2)

        ax3.set_title('Maximum Drawdown Analysis')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('Drawdown (%)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

        # 4. Performance Radar Chart
        ax4 = axes[1, 1]

        # Normalize metrics for radar chart
        metrics = ['Return', 'Win Rate', 'Sharpe', 'Trade Freq']
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle

        ax4 = plt.subplot(2, 2, 4, projection='polar')

        for i, result in enumerate(self.results, 1):
            # Normalize values (0-1 scale)
            values = [
                min(result['return_17d'] / 10, 1.0),  # Normalize to 10% max
                result['win_rate'] / 100,
                min(result['sharpe'] / 3, 1.0),  # Normalize to 3 max
                min(result['trades_per_day'] / 5, 1.0)  # Normalize to 5 trades/day max
            ]
            values += values[:1]  # Complete the circle

            ax4.plot(angles, values, 'o-', linewidth=2, label=f'Iteration {i}')
            ax4.fill(angles, values, alpha=0.25)

        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(metrics)
        ax4.set_ylim(0, 1)
        ax4.set_title('Performance Radar Chart')
        ax4.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

        plt.tight_layout()
        plt.savefig(output_dir / 'risk_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _save_results(self, output_dir: Path):
        """Save detailed results to JSON"""

        # Prepare results for saving
        save_data = {
            'summary': {
                'total_iterations': len(self.results),
                'analysis_date': datetime.now().isoformat(),
                'period_days': 17,
                'starting_capital': 1000.0
            },
            'iterations': []
        }

        for i, result in enumerate(self.results, 1):
            iteration_data = {
                'iteration_number': i,
                'name': result['iteration'],
                'metrics': {
                    'return_17d_pct': round(result['return_17d'], 2),
                    'win_rate_pct': round(result['win_rate'], 1),
                    'sharpe_ratio': round(result['sharpe'], 3),
                    'num_trades': result['num_trades'],
                    'trades_per_day': round(result['trades_per_day'], 2)
                },
                'config': self.trades_data[i]['config'],
                'trade_count_by_reason': {}
            }

            # Count exit reasons
            if result['trades']:
                trades_df = pd.DataFrame(result['trades'])
                exit_reasons = trades_df['exit_reason'].value_counts().to_dict()
                iteration_data['trade_count_by_reason'] = exit_reasons

            save_data['iterations'].append(iteration_data)

        # Save to file
        with open(output_dir / 'backtest_results.json', 'w') as f:
            json.dump(save_data, f, indent=2, default=str)

        print(f"\n💾 Results saved to {output_dir / 'backtest_results.json'}")

if __name__ == '__main__':
    analyzer = BacktestAnalyzer()
    analyzer.run_backtest_and_analyze()