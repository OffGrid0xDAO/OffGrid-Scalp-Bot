"""
Backtesting Engine for Fourier Strategy

This module provides comprehensive backtesting with performance
metrics including Sharpe ratio, win rate, and profit factor.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime


class Backtester:
    """
    Backtesting engine for trading strategies.

    Features:
    - Trade execution simulation
    - Performance metrics calculation
    - Trade log generation
    - Equity curve tracking
    """

    def __init__(self,
                 initial_capital: float = 10000.0,
                 commission: float = 0.001,  # 0.1% per trade
                 slippage: float = 0.0005):   # 0.05% slippage
        """
        Initialize Backtester.

        Args:
            initial_capital: Starting capital (default: $10,000)
            commission: Commission rate per trade (default: 0.1%)
            slippage: Slippage rate (default: 0.05%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def execute_backtest(self,
                        price: pd.Series,
                        trade_signals: pd.DataFrame,
                        position_size: float = 1.0) -> pd.DataFrame:
        """
        Execute backtest on price data with trade signals.

        Args:
            price: Price series
            trade_signals: DataFrame with 'position' column
            position_size: Fraction of capital per trade (default: 1.0 = 100%)

        Returns:
            DataFrame with trade execution details
        """
        df = pd.DataFrame(index=price.index)
        df['price'] = price
        df['position'] = trade_signals['position']

        # Initialize tracking variables
        capital = self.initial_capital
        position = 0
        entry_price = 0
        entry_capital = 0  # Capital at entry
        equity_curve = []
        trades = []
        last_trade_index = -10  # Prevent overtrading

        for i in range(len(df)):
            current_price = df['price'].iloc[i]
            current_position = df['position'].iloc[i]
            prev_position = position

            # Check for position change
            if current_position != prev_position:
                # Close existing position
                if prev_position != 0:
                    exit_price = current_price * (1 - self.slippage * np.sign(prev_position))

                    # Calculate P&L based on entry capital (NOT current capital)
                    price_change = (exit_price - entry_price) / entry_price

                    if prev_position == 1:  # Close long
                        pnl = price_change * entry_capital * position_size
                    else:  # Close short
                        pnl = -price_change * entry_capital * position_size

                    # Apply commission on the position value
                    position_value = entry_capital * position_size
                    commission_cost = position_value * self.commission * 2  # Entry + exit
                    pnl -= commission_cost

                    # Update capital
                    capital += pnl

                    # Prevent negative capital
                    if capital <= 0:
                        capital = 0.01  # Prevent complete wipeout
                        print(f"   ⚠️  Account blown at {df.index[i]}")
                        # Fill remaining equity curve with final value
                        for j in range(i, len(df)):
                            equity_curve.append(capital)
                        break

                    # Record trade
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.index[i],
                        'direction': 'LONG' if prev_position == 1 else 'SHORT',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': (pnl / entry_capital * 100) if entry_capital > 0 else 0,
                        'capital': capital
                    })

                # Open new position or go flat
                if current_position != 0:
                    entry_time = df.index[i]
                    entry_price = current_price * (1 + self.slippage * np.sign(current_position))
                    entry_capital = capital  # Save capital at entry
                    position = current_position
                else:
                    # Going flat - update position to 0
                    position = 0

            # Track equity
            if position == 0:
                equity = capital
            else:
                # Mark-to-market using entry capital
                price_change = (current_price - entry_price) / entry_price

                if position == 1:  # Long
                    unrealized_pnl = price_change * entry_capital * position_size
                else:  # Short
                    unrealized_pnl = -price_change * entry_capital * position_size

                equity = capital + unrealized_pnl

            equity_curve.append(equity)

        # Safety check: ensure equity_curve matches DataFrame length
        while len(equity_curve) < len(df):
            equity_curve.append(equity_curve[-1] if equity_curve else self.initial_capital)

        df['equity'] = equity_curve
        df['returns'] = df['equity'].pct_change()

        # Store trades
        self.trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()

        return df

    def calculate_metrics(self, backtest_results: pd.DataFrame) -> Dict:
        """
        Calculate comprehensive performance metrics.

        Args:
            backtest_results: Results from execute_backtest

        Returns:
            Dictionary with performance metrics
        """
        equity = backtest_results['equity']
        returns = backtest_results['returns'].dropna()

        # Total return
        total_return = (equity.iloc[-1] - self.initial_capital) / self.initial_capital * 100

        # Annualized return (assuming daily data)
        days = len(equity)
        years = days / 252  # Trading days per year
        annualized_return = ((equity.iloc[-1] / self.initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252) * 100

        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe = (annualized_return / volatility) if volatility != 0 else 0

        # Maximum drawdown
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax * 100
        max_drawdown = drawdown.min()

        # Calmar ratio
        calmar = abs(annualized_return / max_drawdown) if max_drawdown != 0 else 0

        # Trade statistics
        if len(self.trades_df) > 0:
            num_trades = len(self.trades_df)
            winning_trades = self.trades_df[self.trades_df['pnl'] > 0]
            losing_trades = self.trades_df[self.trades_df['pnl'] < 0]

            win_rate = len(winning_trades) / num_trades * 100 if num_trades > 0 else 0

            avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
            avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

            # Profit factor
            gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
            gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0

            # Expectancy
            expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)

            # Average holding period
            self.trades_df['holding_period'] = (
                pd.to_datetime(self.trades_df['exit_time']) -
                pd.to_datetime(self.trades_df['entry_time'])
            )
            avg_holding_period = self.trades_df['holding_period'].mean()

        else:
            num_trades = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            expectancy = 0
            avg_holding_period = pd.Timedelta(0)

        metrics = {
            'total_return_pct': total_return,
            'annualized_return_pct': annualized_return,
            'volatility_pct': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'calmar_ratio': calmar,
            'num_trades': num_trades,
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'avg_holding_period': avg_holding_period,
            'final_capital': equity.iloc[-1],
            'days_traded': len(equity)
        }

        return metrics

    def get_trade_log(self) -> pd.DataFrame:
        """
        Get detailed trade log.

        Returns:
            DataFrame with all trades
        """
        return self.trades_df

    def calculate_rolling_metrics(self,
                                  backtest_results: pd.DataFrame,
                                  window: int = 30) -> pd.DataFrame:
        """
        Calculate rolling performance metrics.

        Args:
            backtest_results: Results from execute_backtest
            window: Rolling window size (default: 30)

        Returns:
            DataFrame with rolling metrics
        """
        df = pd.DataFrame(index=backtest_results.index)

        returns = backtest_results['returns']

        # Rolling Sharpe
        rolling_mean = returns.rolling(window=window).mean()
        rolling_std = returns.rolling(window=window).std()
        df['rolling_sharpe'] = (rolling_mean / rolling_std) * np.sqrt(252)

        # Rolling max drawdown
        equity = backtest_results['equity']
        rolling_max = equity.rolling(window=window).max()
        df['rolling_drawdown'] = (equity - rolling_max) / rolling_max * 100

        # Rolling win rate
        if len(self.trades_df) > 0:
            # This is approximate - proper implementation would require trade-by-trade tracking
            rolling_returns = returns.rolling(window=window)
            df['rolling_win_rate'] = (rolling_returns.apply(lambda x: (x > 0).sum() / len(x) * 100))

        return df

    def generate_summary_report(self, metrics: Dict) -> str:
        """
        Generate a text summary report.

        Args:
            metrics: Metrics dictionary from calculate_metrics

        Returns:
            Formatted summary string
        """
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║            FOURIER STRATEGY BACKTEST RESULTS                 ║
╚══════════════════════════════════════════════════════════════╝

PERFORMANCE METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Initial Capital:        ${self.initial_capital:,.2f}
Final Capital:          ${metrics['final_capital']:,.2f}
Total Return:           {metrics['total_return_pct']:.2f}%
Annualized Return:      {metrics['annualized_return_pct']:.2f}%
Volatility (Annual):    {metrics['volatility_pct']:.2f}%

RISK METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sharpe Ratio:          {metrics['sharpe_ratio']:.2f}
Max Drawdown:          {metrics['max_drawdown_pct']:.2f}%
Calmar Ratio:          {metrics['calmar_ratio']:.2f}

TRADE STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Number of Trades:      {metrics['num_trades']}
Win Rate:              {metrics['win_rate_pct']:.2f}%
Profit Factor:         {metrics['profit_factor']:.2f}
Average Win:           ${metrics['avg_win']:.2f}
Average Loss:          ${metrics['avg_loss']:.2f}
Expectancy:            ${metrics['expectancy']:.2f}
Avg Holding Period:    {metrics['avg_holding_period']}

DURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Days Traded:           {metrics['days_traded']}
"""
        return report

    def run_backtest(self,
                    price: pd.Series,
                    trade_signals: pd.DataFrame,
                    position_size: float = 0.25,  # Default 25% of capital per trade
                    verbose: bool = True) -> Dict:
        """
        Run complete backtest and return all results.

        Args:
            price: Price series
            trade_signals: Trade signals DataFrame
            position_size: Position size fraction
            verbose: Print summary report

        Returns:
            Dictionary with backtest_results, metrics, trade_log
        """
        # Execute backtest
        backtest_results = self.execute_backtest(price, trade_signals, position_size)

        # Calculate metrics
        metrics = self.calculate_metrics(backtest_results)

        # Get trade log
        trade_log = self.get_trade_log()

        # Calculate rolling metrics
        rolling_metrics = self.calculate_rolling_metrics(backtest_results)

        # Print summary if verbose
        if verbose:
            report = self.generate_summary_report(metrics)
            print(report)

        return {
            'backtest_results': backtest_results,
            'metrics': metrics,
            'trade_log': trade_log,
            'rolling_metrics': rolling_metrics
        }
