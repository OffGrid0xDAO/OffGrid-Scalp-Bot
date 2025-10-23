#!/usr/bin/env python3
"""
Backtest Engine - Historical Strategy Simulation

Simulates trading strategy on historical data with:
- Realistic order execution (using high/low prices)
- Commission and slippage
- Partial exits and position sizing
- Risk management
- Detailed trade logging

This tells us how our strategy WOULD perform with current parameters.
Compare this to OptimalTradeFinder to see the performance gap!
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from pathlib import Path
import json


class BacktestEngine:
    """
    Backtest trading strategy on historical data

    Realistic simulation including:
    - Entry/exit using high/low prices (not just close)
    - Commission (0.05% default)
    - Slippage (0.02% default)
    - Partial profit taking
    - Position sizing
    - Risk management
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        commission_pct: float = 0.05,
        slippage_pct: float = 0.02,
        position_size_pct: float = 10.0,
        max_concurrent_trades: int = 3,
        max_daily_loss_pct: float = 5.0
    ):
        """
        Initialize backtest engine

        Args:
            initial_capital: Starting capital in USD
            commission_pct: Commission per trade (%)
            slippage_pct: Slippage per trade (%)
            position_size_pct: % of capital per trade
            max_concurrent_trades: Maximum simultaneous positions
            max_daily_loss_pct: Max daily loss before stopping
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.position_size_pct = position_size_pct
        self.max_concurrent_trades = max_concurrent_trades
        self.max_daily_loss_pct = max_daily_loss_pct

        # State
        self.capital = initial_capital
        self.equity_curve = []
        self.trades = []
        self.open_trades = []
        self.daily_pnl = 0
        self.current_date = None

    def reset(self):
        """Reset backtest state"""
        self.capital = self.initial_capital
        self.equity_curve = []
        self.trades = []
        self.open_trades = []
        self.daily_pnl = 0
        self.current_date = None

    def can_enter_trade(self) -> bool:
        """Check if we can enter a new trade"""
        # Check concurrent trades limit
        if len(self.open_trades) >= self.max_concurrent_trades:
            return False

        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss_pct:
            return False

        # Check if we have capital
        if self.capital <= 0:
            return False

        return True

    def enter_trade(
        self,
        entry_signal: Dict,
        entry_candle: pd.Series,
        entry_candle_idx: int,
        exit_manager
    ) -> Dict:
        """
        Enter a new trade

        Args:
            entry_signal: Signal from EntryDetector
            entry_candle: Entry candle data
            entry_candle_idx: Index of entry candle
            exit_manager: ExitManager instance

        Returns:
            Trade dict
        """
        direction = entry_signal['direction']

        # Use realistic entry price (with slippage)
        if direction == 'long':
            # For long, we buy at ask (slightly above close)
            entry_price = entry_candle['close'] * (1 + self.slippage_pct / 100)
        else:
            # For short, we sell at bid (slightly below close)
            entry_price = entry_candle['close'] * (1 - self.slippage_pct / 100)

        # Calculate position size (use INITIAL capital to avoid unrealistic compounding)
        # For scalping/day trading, position size should be consistent, not exponentially growing
        position_size_usd = self.initial_capital * (self.position_size_pct / 100)
        position_size = position_size_usd / entry_price

        # Safety check: can't trade more than available capital
        if position_size_usd > self.capital:
            position_size_usd = self.capital * 0.95  # Use 95% of available capital max
            position_size = position_size_usd / entry_price

        # Commission on entry
        commission = position_size_usd * (self.commission_pct / 100)

        # Calculate exit levels
        df_at_entry = pd.DataFrame([entry_candle])
        exit_levels = exit_manager.calculate_exit_levels(entry_price, direction, df_at_entry)

        # Create trade
        trade = {
            'entry_idx': entry_candle_idx,
            'entry_time': entry_candle['timestamp'],
            'entry_price': entry_price,
            'direction': direction,
            'position_size': position_size,
            'position_size_usd': position_size_usd,
            'entry_commission': commission,
            'remaining_size': 100,  # %
            'exit_levels': exit_levels,
            'exits_taken': [],
            'partial_exits': [],
            'mfe': 0,  # Maximum Favorable Excursion
            'mae': 0,  # Maximum Adverse Excursion
            'confidence': entry_signal.get('confidence', 0),
            'use_trailing_stop': False
        }

        # Deduct commission and lock position capital
        self.capital -= commission
        self.capital -= position_size_usd  # Lock the capital used for this position

        return trade

    def update_trade_mfe_mae(self, trade: Dict, candle: pd.Series):
        """Update Maximum Favorable/Adverse Excursion"""
        entry_price = trade['entry_price']
        direction = trade['direction']

        if direction == 'long':
            profit = (candle['high'] - entry_price) / entry_price * 100
            loss = (candle['low'] - entry_price) / entry_price * 100
        else:
            profit = (entry_price - candle['low']) / entry_price * 100
            loss = (entry_price - candle['high']) / entry_price * 100

        trade['mfe'] = max(trade['mfe'], profit)
        trade['mae'] = min(trade['mae'], loss)

    def exit_trade(
        self,
        trade: Dict,
        exit_info: Dict,
        exit_candle: pd.Series,
        exit_candle_idx: int
    ):
        """
        Execute trade exit (full or partial)

        Args:
            trade: Trade dict
            exit_info: Exit info from ExitManager
            exit_candle: Current candle
            exit_candle_idx: Index of exit candle
        """
        # Use realistic exit price (with slippage)
        if trade['direction'] == 'long':
            # For long exit, we sell at bid
            exit_price = exit_info['exit_price'] * (1 - self.slippage_pct / 100)
        else:
            # For short exit, we buy at ask
            exit_price = exit_info['exit_price'] * (1 + self.slippage_pct / 100)

        # Calculate exit size
        exit_size_pct = exit_info['exit_size']
        exit_size_usd = trade['position_size_usd'] * (exit_size_pct / 100)
        exit_size = trade['position_size'] * (exit_size_pct / 100)

        # Calculate P&L
        if trade['direction'] == 'long':
            pnl_pct = (exit_price - trade['entry_price']) / trade['entry_price'] * 100
        else:
            pnl_pct = (trade['entry_price'] - exit_price) / trade['entry_price'] * 100

        pnl_usd = exit_size_usd * (pnl_pct / 100)

        # Commission on exit
        commission = exit_size_usd * (self.commission_pct / 100)
        pnl_usd -= commission

        # Update capital
        self.capital += exit_size_usd + pnl_usd
        self.daily_pnl += pnl_usd / self.initial_capital * 100

        # Record partial exit
        partial_exit = {
            'exit_idx': exit_candle_idx,
            'exit_time': exit_candle['timestamp'],
            'exit_type': exit_info['exit_type'],
            'exit_price': exit_price,
            'exit_size_pct': exit_size_pct,
            'exit_size_usd': exit_size_usd,
            'pnl_pct': pnl_pct,
            'pnl_usd': pnl_usd,
            'commission': commission,
            'candles_held': exit_candle_idx - trade['entry_idx']
        }
        trade['partial_exits'].append(partial_exit)
        trade['remaining_size'] -= exit_size_pct

        # Mark exit taken
        trade['exits_taken'].append(exit_info['exit_type'])

        return pnl_usd, pnl_pct

    def run_backtest(
        self,
        df: pd.DataFrame,
        entry_detector,
        exit_manager,
        ribbon_analyzer=None,
        verbose: bool = True
    ) -> Dict:
        """
        Run full backtest on historical data

        Args:
            df: DataFrame with all indicators
            entry_detector: EntryDetector instance
            exit_manager: ExitManager instance
            ribbon_analyzer: Optional RibbonAnalyzer instance
            verbose: Print progress

        Returns:
            dict with backtest results:
                - trades: list of all trades
                - equity_curve: capital over time
                - metrics: performance metrics
        """
        if verbose:
            print("\n" + "="*80)
            print("RUNNING BACKTEST")
            print("="*80)
            print(f"   Initial capital: ${self.initial_capital:,.2f}")
            print(f"   Position size: {self.position_size_pct}%")
            print(f"   Commission: {self.commission_pct}%")
            print(f"   Slippage: {self.slippage_pct}%")
            print(f"   Max concurrent trades: {self.max_concurrent_trades}")

        # Reset state
        self.reset()

        # Add ribbon analysis if needed
        if ribbon_analyzer and 'compression_score' not in df.columns:
            df = ribbon_analyzer.analyze_all(df)

        # Scan for entries
        signals_df = entry_detector.scan_historical_signals(df)

        # Simulate trading
        for i in range(len(signals_df)):
            current_candle = signals_df.iloc[i]

            # Check daily reset
            if self.current_date is None:
                self.current_date = current_candle['timestamp'][:10]
            elif current_candle['timestamp'][:10] != self.current_date:
                self.current_date = current_candle['timestamp'][:10]
                self.daily_pnl = 0

            # Update existing trades
            for trade in self.open_trades[:]:  # Copy list to allow removal
                # Update MFE/MAE
                self.update_trade_mfe_mae(trade, current_candle)

                # Check exit
                candles_held = i - trade['entry_idx']
                exit_info = exit_manager.check_exit(trade, current_candle, candles_held)

                if exit_info['should_exit']:
                    pnl_usd, pnl_pct = self.exit_trade(trade, exit_info, current_candle, i)

                    # If fully exited, close trade
                    if trade['remaining_size'] <= 0:
                        # Calculate total P&L
                        total_pnl_usd = sum(e['pnl_usd'] for e in trade['partial_exits'])
                        total_commission = trade['entry_commission'] + sum(e['commission'] for e in trade['partial_exits'])

                        # Finalize trade
                        trade['status'] = 'closed'
                        trade['total_pnl_usd'] = total_pnl_usd
                        trade['total_pnl_pct'] = total_pnl_usd / trade['position_size_usd'] * 100
                        trade['total_commission'] = total_commission
                        trade['final_exit_time'] = current_candle['timestamp']
                        trade['final_exit_idx'] = i

                        # Move to closed trades
                        self.trades.append(trade)
                        self.open_trades.remove(trade)

            # Check for new entry signal
            if current_candle.get('entry_signal') and self.can_enter_trade():
                # Get entry signal
                entry_signal = {
                    'signal': True,
                    'direction': current_candle['entry_direction'],
                    'confidence': current_candle['entry_confidence']
                }

                # Enter trade
                trade = self.enter_trade(entry_signal, current_candle, i, exit_manager)
                self.open_trades.append(trade)

            # Record equity
            self.equity_curve.append({
                'timestamp': current_candle['timestamp'],
                'capital': self.capital,
                'open_trades': len(self.open_trades)
            })

        # Close any remaining open trades at last candle
        if self.open_trades:
            last_candle = signals_df.iloc[-1]
            for trade in self.open_trades:
                # Force close at market
                exit_info = {
                    'exit_type': 'forced_close',
                    'exit_price': last_candle['close'],
                    'exit_size': trade['remaining_size']
                }
                pnl_usd, pnl_pct = self.exit_trade(trade, exit_info, last_candle, len(signals_df) - 1)

                # Finalize
                total_pnl_usd = sum(e['pnl_usd'] for e in trade['partial_exits'])
                trade['status'] = 'forced_close'
                trade['total_pnl_usd'] = total_pnl_usd
                trade['total_pnl_pct'] = total_pnl_usd / trade['position_size_usd'] * 100
                self.trades.append(trade)

            self.open_trades = []

        # Calculate metrics
        metrics = self.calculate_metrics()

        if verbose:
            self.print_summary(metrics)

        return {
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'metrics': metrics
        }

    def calculate_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {}

        # Basic stats
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['total_pnl_usd'] > 0]
        losing_trades = [t for t in self.trades if t['total_pnl_usd'] <= 0]

        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        # P&L stats
        total_pnl = sum(t['total_pnl_usd'] for t in self.trades)
        total_return = total_pnl / self.initial_capital * 100

        avg_win = np.mean([t['total_pnl_usd'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['total_pnl_usd'] for t in losing_trades]) if losing_trades else 0

        # Profit factor
        gross_profit = sum(t['total_pnl_usd'] for t in winning_trades)
        gross_loss = abs(sum(t['total_pnl_usd'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Max drawdown
        equity = [self.initial_capital] + [e['capital'] for e in self.equity_curve]
        peak = self.initial_capital
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak * 100
            max_dd = max(max_dd, dd)

        # MFE/MAE analysis
        avg_mfe = np.mean([t['mfe'] for t in self.trades])
        avg_mae = np.mean([t['mae'] for t in self.trades])

        # Calculate proper final capital (should match initial + total_pnl)
        expected_final = self.initial_capital + total_pnl

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'final_capital': expected_final,  # Use calculated value, not self.capital (may have locked funds)
            'avg_mfe': avg_mfe,
            'avg_mae': avg_mae
        }

    def print_summary(self, metrics: Dict):
        """Print backtest summary"""
        print("\n" + "="*80)
        print("BACKTEST RESULTS")
        print("="*80)
        print(f"\n💰 P&L Summary:")
        print(f"   Initial capital: ${self.initial_capital:,.2f}")
        print(f"   Final capital: ${metrics['final_capital']:,.2f}")
        print(f"   Total P&L: ${metrics['total_pnl']:,.2f} ({metrics['total_return']:+.2f}%)")

        print(f"\n📊 Trade Statistics:")
        print(f"   Total trades: {metrics['total_trades']}")
        print(f"   Winning trades: {metrics['winning_trades']}")
        print(f"   Losing trades: {metrics['losing_trades']}")
        print(f"   Win rate: {metrics['win_rate']:.1f}%")

        print(f"\n📈 Performance Metrics:")
        print(f"   Average win: ${metrics['avg_win']:,.2f}")
        print(f"   Average loss: ${metrics['avg_loss']:,.2f}")
        print(f"   Profit factor: {metrics['profit_factor']:.2f}")
        print(f"   Max drawdown: {metrics['max_drawdown']:.2f}%")

        print(f"\n🎯 MFE/MAE Analysis:")
        print(f"   Average MFE: {metrics['avg_mfe']:.2f}%")
        print(f"   Average MAE: {metrics['avg_mae']:.2f}%")


if __name__ == '__main__':
    """Test backtest engine"""
    print("Backtest Engine - Test Mode")
    print("To run backtest, use: python3 scripts/run_backtest.py")
