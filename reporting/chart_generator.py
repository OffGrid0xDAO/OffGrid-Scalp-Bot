#!/usr/bin/env python3
"""
Chart Generator - Professional Day Trading Analysis

Creates comprehensive comparison charts showing:
- Price action with Bollinger Bands and VWAP overlays
- Optimal trade entry/exit points
- Backtest trade entry/exit points
- Actual trade entry/exit points
- Professional indicators: Stochastic (5-3-3), RSI, Confluence
- Volume analysis with status colors
- Performance comparison metrics

Optimized for 2-3 trades/day strategy visualization
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from typing import List, Dict
import os


class ChartGenerator:
    """
    Generate comparison charts for optimization analysis
    """

    def __init__(self, output_dir: str = None):
        """
        Initialize chart generator

        Args:
            output_dir: Directory to save charts (default: charts/optimization)
        """
        if output_dir is None:
            output_dir = Path.cwd() / 'charts' / 'optimization'

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_3way_comparison_chart(
        self,
        df: pd.DataFrame,
        optimal_trades: List[Dict],
        backtest_trades: List[Dict],
        actual_trades: List[Dict] = None,
        timeframe: str = '1h',
        symbol: str = 'ETH',
        candles_to_show: int = 500
    ) -> str:
        """
        Create 3-way comparison chart

        Args:
            df: Price data with indicators
            optimal_trades: Optimal trades from MFE analysis
            backtest_trades: Backtest simulation trades
            actual_trades: Live trading trades (optional)
            timeframe: Timeframe
            symbol: Trading symbol
            candles_to_show: Number of recent candles to display

        Returns:
            str: Path to generated chart
        """
        print(f"\n📊 Creating 3-way comparison chart...")

        # Filter to recent candles
        df_plot = df.tail(candles_to_show).copy()

        # Create figure with subplots (added RSI and Stochastic)
        fig = make_subplots(
            rows=6, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.40, 0.15, 0.12, 0.12, 0.12, 0.09],
            subplot_titles=(
                f'{symbol} {timeframe} - Professional Day Trading Analysis',
                'Confluence Scores',
                'RSI (14)',
                'Stochastic (5-3-3)',
                'Volume Status',
                'Performance Comparison'
            )
        )

        # Panel 1: Price with trade markers + Bollinger Bands + VWAP
        self._add_price_panel(fig, df_plot, optimal_trades, backtest_trades, actual_trades, row=1)

        # Panel 2: Confluence scores
        self._add_confluence_panel(fig, df_plot, row=2)

        # Panel 3: RSI
        self._add_rsi_panel(fig, df_plot, row=3)

        # Panel 4: Stochastic Oscillator (NEW)
        self._add_stochastic_panel(fig, df_plot, row=4)

        # Panel 5: Volume
        self._add_volume_panel(fig, df_plot, row=5)

        # Panel 6: Performance comparison
        self._add_performance_panel(
            fig,
            optimal_trades,
            backtest_trades,
            actual_trades,
            row=6
        )

        # Update layout
        fig.update_layout(
            title=f'{symbol} {timeframe} - Professional Day Trading Analysis (Stochastic, Bollinger, VWAP)',
            xaxis_rangeslider_visible=False,
            height=1600,  # Increased for 6 panels
            showlegend=True,
            hovermode='x unified',
            template='plotly_dark',
            font=dict(size=10)
        )

        # Save chart
        output_file = self.output_dir / f'{symbol}_{timeframe}_3way_comparison.html'
        fig.write_html(str(output_file))

        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"   ✅ Chart saved: {output_file} ({file_size:.1f} MB)")

        return str(output_file)

    def _add_price_panel(
        self,
        fig,
        df: pd.DataFrame,
        optimal_trades: List[Dict],
        backtest_trades: List[Dict],
        actual_trades: List[Dict],
        row: int
    ):
        """Add price chart with trade entry/exit markers

        NOTE: Order matters for layering!
        1. Candlesticks (bottom layer)
        2. Indicators (Bollinger, VWAP, EMA)
        3. Trade markers (top layer - added LAST)
        """

        # LAYER 1: Candlesticks (bottom)
        fig.add_trace(
            go.Candlestick(
                x=df['timestamp'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                showlegend=True,
                increasing_line_color='green',
                decreasing_line_color='red'
            ),
            row=row, col=1
        )

        # LAYER 2: Indicators (middle layer)
        # Add Bollinger Bands
        if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
            # Lower band first (for fill to work properly)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['bb_lower'],
                    name='BB Lower',
                    line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
                    showlegend=True
                ),
                row=row, col=1
            )

            # Upper band with fill
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['bb_upper'],
                    name='BB Upper',
                    line=dict(color='rgba(150, 150, 150, 0.5)', width=1, dash='dot'),
                    fill='tonexty',
                    fillcolor='rgba(150, 150, 150, 0.1)',
                    showlegend=True
                ),
                row=row, col=1
            )

            # Middle band (SMA)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['bb_middle'],
                    name='BB Middle',
                    line=dict(color='gray', width=1),
                    showlegend=True
                ),
                row=row, col=1
            )

        # Add VWAP
        if 'vwap' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['vwap'],
                    name='VWAP',
                    line=dict(color='purple', width=2, dash='dash'),
                    showlegend=True
                ),
                row=row, col=1
            )

        # Add EMA20 for reference
        if 'MMA20_value' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['MMA20_value'],
                    name='EMA20 (Yellow)',
                    line=dict(color='yellow', width=1.5),
                    showlegend=True
                ),
                row=row, col=1
            )

        # LAYER 3: Trade markers (TOP LAYER - rendered last so they appear on top!)
        # This is critical - markers MUST be added AFTER all price/indicator lines

        # Optimal trade markers (Green - perfect hindsight)
        if optimal_trades:
            for trade in optimal_trades:
                direction = trade.get('direction', 'long')
                entry_idx = trade.get('entry_idx')
                exit_idx = trade.get('optimal_exit_idx')

                # Entry marker (Long = triangle-up green, Short = triangle-down red)
                if entry_idx and entry_idx < len(df):
                    if direction == 'long':
                        symbol, color = 'triangle-up', 'lime'
                        name = 'Optimal Long Open'
                    else:
                        symbol, color = 'triangle-down', 'red'
                        name = 'Optimal Short Open'

                    fig.add_trace(
                        go.Scatter(
                            x=[df.iloc[entry_idx]['timestamp']],
                            y=[trade['entry_price']],
                            mode='markers+text',
                            marker=dict(
                                symbol=symbol,
                                size=18,  # Increased from 14
                                color=color,
                                line=dict(width=3, color='white'),
                                opacity=1.0  # Fully opaque
                            ),
                            text=['O'],  # O = Open
                            textposition='top center',
                            textfont=dict(size=10, color='white', family='Arial Black'),
                            name=name,
                            showlegend=False,
                            hovertemplate=f'<b>Optimal {direction.upper()} Entry</b><br>' +
                                        f'Price: {trade["entry_price"]:.2f}<br>' +
                                        '<extra></extra>'
                        ),
                        row=row, col=1
                    )

                # Exit marker (Long = X green, Short = X red)
                if exit_idx and exit_idx < len(df):
                    if direction == 'long':
                        symbol, color = 'x', 'lime'
                        name = 'Optimal Long Close'
                    else:
                        symbol, color = 'x', 'red'
                        name = 'Optimal Short Close'

                    fig.add_trace(
                        go.Scatter(
                            x=[df.iloc[exit_idx]['timestamp']],
                            y=[trade['optimal_exit_price']],
                            mode='markers+text',
                            marker=dict(
                                symbol=symbol,
                                size=18,  # Increased from 14
                                color=color,
                                line=dict(width=3, color='white'),
                                opacity=1.0  # Fully opaque
                            ),
                            text=['C'],  # C = Close
                            textposition='bottom center',
                            textfont=dict(size=10, color='white', family='Arial Black'),
                            name=name,
                            showlegend=False,
                            hovertemplate=f'<b>Optimal {direction.upper()} Exit</b><br>' +
                                        f'Price: {trade["optimal_exit_price"]:.2f}<br>' +
                                        f'Profit: {trade.get("profit_pct", 0):.2f}%<br>' +
                                        '<extra></extra>'
                        ),
                        row=row, col=1
                    )

        # Backtest trade markers (Orange/Blue - simulated)
        if backtest_trades:
            for trade in backtest_trades:
                direction = trade.get('direction', 'long')
                entry_idx = trade.get('entry_idx')

                # Entry marker (Long = circle orange, Short = circle blue)
                if entry_idx and entry_idx < len(df):
                    if direction == 'long':
                        symbol, color = 'circle', 'orange'
                        name = 'Backtest Long Open'
                    else:
                        symbol, color = 'circle', 'cyan'
                        name = 'Backtest Short Open'

                    fig.add_trace(
                        go.Scatter(
                            x=[df.iloc[entry_idx]['timestamp']],
                            y=[trade['entry_price']],
                            mode='markers+text',
                            marker=dict(
                                symbol=symbol,
                                size=14,  # Increased from 10
                                color=color,
                                line=dict(width=2, color='white'),
                                opacity=1.0  # Fully opaque
                            ),
                            text=['B'],  # B = Backtest
                            textposition='top center',
                            textfont=dict(size=9, color='white', family='Arial Black'),
                            name=name,
                            showlegend=False,
                            hovertemplate=f'<b>Backtest {direction.upper()} Entry</b><br>' +
                                        f'Price: {trade["entry_price"]:.2f}<br>' +
                                        '<extra></extra>'
                        ),
                        row=row, col=1
                    )

                # Backtest exits (final exit only for clarity)
                if 'partial_exits' in trade and trade['partial_exits']:
                    # Show only final exit to reduce clutter
                    final_exit = trade['partial_exits'][-1]
                    exit_idx = final_exit.get('exit_idx')
                    if exit_idx and exit_idx < len(df):
                        if direction == 'long':
                            symbol, color = 'square', 'orange'
                            name = 'Backtest Long Close'
                        else:
                            symbol, color = 'square', 'cyan'
                            name = 'Backtest Short Close'

                        fig.add_trace(
                            go.Scatter(
                                x=[df.iloc[exit_idx]['timestamp']],
                                y=[final_exit['exit_price']],
                                mode='markers+text',
                                marker=dict(
                                    symbol=symbol,
                                    size=12,  # Increased from 8
                                    color=color,
                                    line=dict(width=2, color='white'),
                                    opacity=1.0  # Fully opaque
                                ),
                                text=['C'],  # C = Close
                                textposition='bottom center',
                                textfont=dict(size=9, color='white', family='Arial Black'),
                                name=name,
                                showlegend=False,
                                hovertemplate=f'<b>Backtest {direction.upper()} Exit</b><br>' +
                                            f'Price: {final_exit["exit_price"]:.2f}<br>' +
                                            f'Type: {final_exit.get("exit_type", "N/A")}<br>' +
                                            '<extra></extra>'
                            ),
                            row=row, col=1
                        )

        # Actual trade markers (Cyan - live)
        if actual_trades:
            for trade in actual_trades:
                # Entry
                entry_time = trade.get('entry_time')
                if entry_time:
                    fig.add_trace(
                        go.Scatter(
                            x=[entry_time],
                            y=[trade['entry_price']],
                            mode='markers+text',
                            marker=dict(
                                symbol='star',
                                size=16,  # Increased from 12
                                color='cyan',
                                line=dict(width=3, color='white'),
                                opacity=1.0  # Fully opaque
                            ),
                            text=['A'],  # A = Actual
                            textposition='top center',
                            textfont=dict(size=10, color='white', family='Arial Black'),
                            name='Actual Entry',
                            showlegend=False,
                            hovertemplate='<b>Actual Entry</b><br>' +
                                        f'Price: {trade["entry_price"]:.2f}<br>' +
                                        '<extra></extra>'
                        ),
                        row=row, col=1
                    )

    def _add_confluence_panel(self, fig, df: pd.DataFrame, row: int):
        """Add confluence score panel"""
        if 'confluence_score_long' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['confluence_score_long'],
                    name='Long Score',
                    line=dict(color='green', width=1),
                    fill='tozeroy',
                    showlegend=False
                ),
                row=row, col=1
            )

        if 'confluence_score_short' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['confluence_score_short'],
                    name='Short Score',
                    line=dict(color='red', width=1),
                    fill='tozeroy',
                    showlegend=False
                ),
                row=row, col=1
            )

        # Threshold line
        fig.add_hline(y=30, line_dash="dash", line_color="yellow", opacity=0.5, row=row, col=1)

    def _add_rsi_panel(self, fig, df: pd.DataFrame, row: int):
        """Add RSI panel with overbought/oversold zones"""
        if 'rsi_14' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['rsi_14'],
                    name='RSI(14)',
                    line=dict(color='cyan', width=2),
                    showlegend=False
                ),
                row=row, col=1
            )

            # Overbought line (70)
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=row, col=1)

            # Oversold line (30)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=row, col=1)

            # Middle line (50)
            fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=row, col=1)

    def _add_stochastic_panel(self, fig, df: pd.DataFrame, row: int):
        """Add Stochastic Oscillator panel (NEW - Professional Day Trading Indicator)"""
        if 'stoch_k' in df.columns and 'stoch_d' in df.columns:
            # %K line (fast)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['stoch_k'],
                    name='Stoch %K',
                    line=dict(color='#00BFFF', width=2),  # Deep sky blue
                    showlegend=False
                ),
                row=row, col=1
            )

            # %D line (slow)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['stoch_d'],
                    name='Stoch %D',
                    line=dict(color='#FF6347', width=2, dash='dash'),  # Tomato red
                    showlegend=False
                ),
                row=row, col=1
            )

            # Overbought zone (80)
            fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.5, row=row, col=1)

            # Oversold zone (20)
            fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.5, row=row, col=1)

            # Middle line (50)
            fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=row, col=1)

            # Add shaded overbought/oversold regions
            fig.add_hrect(y0=80, y1=100, fillcolor="red", opacity=0.1, line_width=0, row=row, col=1)
            fig.add_hrect(y0=0, y1=20, fillcolor="green", opacity=0.1, line_width=0, row=row, col=1)

    def _add_volume_panel(self, fig, df: pd.DataFrame, row: int):
        """Add volume panel with status colors"""
        colors = []
        for status in df['volume_status']:
            if status == 'spike':
                colors.append('red')
            elif status == 'elevated':
                colors.append('orange')
            elif status == 'low':
                colors.append('gray')
            else:
                colors.append('blue')

        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['volume'],
                name='Volume',
                marker_color=colors,
                showlegend=False
            ),
            row=row, col=1
        )

    def _add_performance_panel(
        self,
        fig,
        optimal_trades: List[Dict],
        backtest_trades: List[Dict],
        actual_trades: List[Dict],
        row: int
    ):
        """Add performance comparison bars"""

        categories = ['Optimal', 'Backtest', 'Actual']

        # Calculate metrics
        optimal_count = len(optimal_trades) if optimal_trades else 0
        optimal_pnl = sum(t['profit_pct'] for t in optimal_trades) if optimal_trades else 0
        optimal_win_rate = 100.0  # Optimal is perfect by definition

        backtest_count = len(backtest_trades) if backtest_trades else 0
        backtest_pnl = sum(t.get('total_pnl_pct', 0) for t in backtest_trades) if backtest_trades else 0
        backtest_winners = sum(1 for t in backtest_trades if t.get('total_pnl_pct', 0) > 0) if backtest_trades else 0
        backtest_win_rate = (backtest_winners / backtest_count * 100) if backtest_count > 0 else 0

        actual_count = len(actual_trades) if actual_trades else 0
        actual_win_rate = 0  # TODO: calculate from actual

        # Trade count bars
        fig.add_trace(
            go.Bar(
                x=categories,
                y=[optimal_count, backtest_count, actual_count],
                name='Trade Count',
                marker_color=['lime', 'yellow', 'cyan'],
                showlegend=False
            ),
            row=row, col=1
        )

    def create_equity_curve_comparison(
        self,
        backtest_equity: List[Dict],
        actual_equity: List[Dict] = None,
        symbol: str = 'ETH',
        timeframe: str = '1h'
    ) -> str:
        """
        Create equity curve comparison chart

        Args:
            backtest_equity: Equity curve from backtest
            actual_equity: Equity curve from live trading
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            str: Path to generated chart
        """
        print(f"\n📈 Creating equity curve comparison...")

        fig = go.Figure()

        # Backtest equity curve
        if backtest_equity:
            timestamps = [e['timestamp'] for e in backtest_equity]
            capital = [e['capital'] for e in backtest_equity]

            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=capital,
                    name='Backtest Equity',
                    line=dict(color='yellow', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(255, 255, 0, 0.1)'
                )
            )

        # Actual equity curve
        if actual_equity:
            timestamps = [e['timestamp'] for e in actual_equity]
            capital = [e['capital'] for e in actual_equity]

            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=capital,
                    name='Actual Equity',
                    line=dict(color='cyan', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(0, 255, 255, 0.1)'
                )
            )

        fig.update_layout(
            title=f'{symbol} {timeframe} - Equity Curve Comparison',
            xaxis_title='Time',
            yaxis_title='Capital ($)',
            template='plotly_dark',
            height=600
        )

        # Save
        output_file = self.output_dir / f'{symbol}_{timeframe}_equity_curve.html'
        fig.write_html(str(output_file))

        print(f"   ✅ Equity chart saved: {output_file}")
        return str(output_file)


if __name__ == '__main__':
    """Test chart generator"""
    print("Chart Generator - Test Mode")

    generator = ChartGenerator()
    print(f"✅ Charts will be saved to: {generator.output_dir}")
