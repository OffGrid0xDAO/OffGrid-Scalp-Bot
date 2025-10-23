"""
Interactive Trading Analysis Visualization
Shows price, EMAs with colors, derivatives, and trade signals (optimal vs actual)
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json


class TradingVisualizer:
    """Visualize trading data with EMAs, derivatives, and trade signals"""

    def __init__(self, ema_data_file='trading_data/ema_data_5min.csv',
                 decisions_file='trading_data/claude_decisions.csv',
                 optimal_trades_file='trading_data/optimal_trades.json',
                 backtest_trades_file='trading_data/backtest_trades.json'):
        """
        Initialize visualizer

        Args:
            ema_data_file: Path to EMA data CSV
            decisions_file: Path to Claude decisions CSV
            optimal_trades_file: Path to optimal trades JSON
            backtest_trades_file: Path to backtest trades JSON
        """
        self.ema_data_file = ema_data_file
        self.decisions_file = decisions_file
        self.optimal_trades_file = optimal_trades_file
        self.backtest_trades_file = backtest_trades_file

        self.df = None
        self.decisions = None
        self.optimal_trades = None
        self.backtest_trades = None

    def load_data(self):
        """Load all data files"""
        print("📂 Loading data files...")

        # Load EMA data
        try:
            # Handle corrupted lines in CSV
            self.df = pd.read_csv(self.ema_data_file, on_bad_lines='skip')
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], errors='coerce')
            self.df = self.df.dropna(subset=['timestamp'])
            self.df = self.df.sort_values('timestamp').reset_index(drop=True)
            print(f"✅ Loaded {len(self.df)} EMA snapshots")
        except FileNotFoundError:
            print(f"❌ EMA data file not found: {self.ema_data_file}")
            return False

        # Load Claude decisions
        try:
            self.decisions = pd.read_csv(self.decisions_file)
            self.decisions['timestamp'] = pd.to_datetime(self.decisions['timestamp'])
            print(f"✅ Loaded {len(self.decisions)} trading decisions")
        except FileNotFoundError:
            print(f"⚠️  No decisions file found (optional): {self.decisions_file}")
            self.decisions = None

        # Load optimal trades
        try:
            with open(self.optimal_trades_file, 'r') as f:
                data = json.load(f)
                self.optimal_trades = data.get('trades', [])
            print(f"✅ Loaded {len(self.optimal_trades)} optimal trades")
        except FileNotFoundError:
            print(f"⚠️  No optimal trades file found (optional): {self.optimal_trades_file}")
            self.optimal_trades = None

        # Load backtest trades
        try:
            with open(self.backtest_trades_file, 'r') as f:
                data = json.load(f)
                self.backtest_trades = data.get('trades', [])
            print(f"✅ Loaded {len(self.backtest_trades)} backtest trades")
        except FileNotFoundError:
            print(f"⚠️  No backtest trades file found (optional): {self.backtest_trades_file}")
            self.backtest_trades = None

        return True

    def get_ema_columns(self):
        """Get all EMA column groups"""
        ema_periods = []
        for col in self.df.columns:
            if col.startswith('MMA') and col.endswith('_value'):
                period = int(col.replace('MMA', '').replace('_value', ''))
                ema_periods.append(period)

        return sorted(ema_periods)

    def get_all_28_emas(self):
        """Get the standard 28 EMAs used in the system"""
        return [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70,
                75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]

    def create_visualization(self, hours_back=12, show_all_emas=True):
        """
        Create interactive visualization

        Args:
            hours_back: How many hours of data to show (default: 12)
            show_all_emas: If True, show all 28 EMAs (default: True)
        """
        print(f"\n📊 Creating visualization for last {hours_back} hours...")

        # Filter to recent data
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        df_viz = self.df[self.df['timestamp'] >= cutoff_time].copy()

        if len(df_viz) == 0:
            print("❌ No data in selected time range")
            return None

        print(f"📈 Visualizing {len(df_viz)} data points")

        # Create subplots
        # 1. Main chart (price + EMAs)
        # 2. Derivative slopes (fast EMAs)
        # 3. Compression state
        # 4. Inflection signals
        fig = make_subplots(
            rows=4, cols=1,
            row_heights=[0.5, 0.2, 0.15, 0.15],
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(
                'Price & EMA Ribbon (28 EMAs) with Trade Signals',
                'EMA Derivatives (Slope) - Fast EMAs',
                'Compression State',
                'Inflection Signals'
            )
        )

        # Plot 1: Price line
        fig.add_trace(
            go.Scatter(
                x=df_viz['timestamp'],
                y=df_viz['price'],
                name='Price',
                line=dict(color='white', width=3),
                mode='lines'
            ),
            row=1, col=1
        )

        # Plot 2: EMAs with colors
        ema_periods = self.get_ema_columns()

        # Define which EMAs to show
        if show_all_emas:
            # Show all 28 standard EMAs
            emas_to_plot = self.get_all_28_emas()
            emas_to_plot = [e for e in emas_to_plot if e in ema_periods]
        else:
            # Show key EMAs only
            emas_to_plot = [5, 10, 15, 20, 25, 30, 40, 50, 100]
            emas_to_plot = [e for e in emas_to_plot if e in ema_periods]

        print(f"📊 Plotting {len(emas_to_plot)} EMAs")

        # Color mapping for EMAs
        color_map = {
            'green': '#00ff00',
            'light_green': '#90EE90',
            'dark_green': '#006400',
            'red': '#ff0000',
            'light_red': '#FFB6C1',
            'dark_red': '#8B0000',
            'yellow': '#ffff00',
            'gray': '#808080',
            'unknown': '#404040'
        }

        for ema_period in emas_to_plot:
            value_col = f'MMA{ema_period}_value'
            color_col = f'MMA{ema_period}_color'
            intensity_col = f'MMA{ema_period}_intensity'

            if value_col not in df_viz.columns:
                continue

            # Get EMA values
            ema_values = df_viz[value_col].copy()

            # Determine line width (faster EMAs = thicker)
            if ema_period <= 20:
                width = 2
            elif ema_period <= 50:
                width = 1.5
            else:
                width = 1

            # Plot EMA with dynamic color changes
            if color_col in df_viz.columns:
                # We'll create segments for each color change
                self._add_ema_with_color_changes(
                    fig, df_viz, ema_period, value_col, color_col,
                    intensity_col, width, color_map, row=1
                )
            else:
                # Fallback: single color line
                fig.add_trace(
                    go.Scatter(
                        x=df_viz['timestamp'],
                        y=ema_values,
                        name=f'EMA{ema_period}',
                        line=dict(
                            color='#808080',
                            width=width,
                            shape='spline',
                            smoothing=0.3
                        ),
                        mode='lines',
                        opacity=0.7
                    ),
                    row=1, col=1
                )

        # Plot 3: Add optimal trade signals (if available)
        if self.optimal_trades:
            self._add_optimal_trades(fig, df_viz, row=1)

        # Plot 4: Add backtest trade signals (if available)
        if self.backtest_trades:
            self._add_backtest_trades(fig, df_viz, row=1)

        # Plot 5: Add actual trade signals from decisions (if available)
        if self.decisions is not None:
            self._add_actual_trades(fig, df_viz, row=1)

        # Plot 6: Derivative slopes for fast EMAs
        self._add_derivative_slopes(fig, df_viz, row=2)

        # Plot 6: Compression state
        self._add_compression_state(fig, df_viz, row=3)

        # Plot 7: Inflection signals
        self._add_inflection_signals(fig, df_viz, row=4)

        # Update layout
        fig.update_layout(
            title=f'Trading Analysis - Last {hours_back} Hours',
            xaxis4_title='Time',
            height=1200,
            template='plotly_dark',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.01
            )
        )

        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Slope", row=2, col=1)
        fig.update_yaxes(title_text="Compression %", row=3, col=1)
        fig.update_yaxes(title_text="Signals", row=4, col=1)

        return fig

    def _add_ema_with_color_changes(self, fig, df_viz, ema_period, value_col, color_col, intensity_col, width, color_map, row=1):
        """
        Add EMA line with dynamic color changes based on CSV color column

        Creates separate line segments for each color to show transitions
        """
        # Get data
        timestamps = df_viz['timestamp'].values
        values = df_viz[value_col].values
        colors = df_viz[color_col].values

        # Get intensity if available
        if intensity_col in df_viz.columns:
            intensities = df_viz[intensity_col].values
        else:
            intensities = ['normal'] * len(values)

        # Find color change points
        segments = []
        current_segment = {
            'start_idx': 0,
            'color': colors[0],
            'intensity': intensities[0]
        }

        for i in range(1, len(colors)):
            # Check if color or intensity changed
            if colors[i] != current_segment['color'] or intensities[i] != current_segment['intensity']:
                # Save current segment
                current_segment['end_idx'] = i
                segments.append(current_segment)

                # Start new segment
                current_segment = {
                    'start_idx': i,
                    'color': colors[i],
                    'intensity': intensities[i]
                }

        # Add final segment
        current_segment['end_idx'] = len(colors)
        segments.append(current_segment)

        # Plot each segment
        for seg_idx, segment in enumerate(segments):
            start = segment['start_idx']
            end = segment['end_idx']

            # Determine color based on color + intensity
            base_color = segment['color']
            intensity = segment['intensity']

            # Map to hex color
            if intensity == 'light':
                if base_color == 'green':
                    line_color = '#90EE90'  # Light green
                elif base_color == 'red':
                    line_color = '#FFB6C1'  # Light red
                else:
                    line_color = color_map.get(base_color, '#808080')
            elif intensity == 'dark':
                if base_color == 'green':
                    line_color = '#006400'  # Dark green
                elif base_color == 'red':
                    line_color = '#8B0000'  # Dark red
                else:
                    line_color = color_map.get(base_color, '#808080')
            else:
                # Normal intensity or unknown
                line_color = color_map.get(base_color, '#808080')

            # Create segment (include one point overlap for continuity)
            if end < len(timestamps):
                seg_timestamps = timestamps[start:end+1]
                seg_values = values[start:end+1]
            else:
                seg_timestamps = timestamps[start:end]
                seg_values = values[start:end]

            # Only show legend for first segment
            show_legend = (seg_idx == 0)

            fig.add_trace(
                go.Scatter(
                    x=seg_timestamps,
                    y=seg_values,
                    name=f'EMA{ema_period}' if show_legend else None,
                    line=dict(
                        color=line_color,
                        width=width,
                        shape='spline',
                        smoothing=0.3
                    ),
                    mode='lines',
                    opacity=0.8,
                    showlegend=show_legend,
                    legendgroup=f'ema{ema_period}',
                    hovertemplate=f'EMA{ema_period}: %{{y:.2f}}<br>Color: {base_color} ({intensity})<extra></extra>'
                ),
                row=row, col=1
            )

    def _add_optimal_trades(self, fig, df_viz, row=1):
        """Add optimal trade entry/exit markers"""
        print("📍 Adding optimal trade signals...")

        for trade in self.optimal_trades:
            # Entry signal
            entry_time = pd.to_datetime(trade['entry_time'])
            entry_price = trade['entry_price']

            # Find closest timestamp in data
            time_diff = abs(df_viz['timestamp'] - entry_time)
            if time_diff.min() < pd.Timedelta(minutes=5):
                closest_idx = time_diff.idxmin()
                timestamp = df_viz.loc[closest_idx, 'timestamp']

                # Green marker for LONG, Red marker for SHORT
                if trade['direction'].upper() == 'LONG':
                    marker_color = 'lime'
                    marker_symbol = 'triangle-up'
                    text = f"📈 OPTIMAL LONG<br>Entry: ${entry_price:.2f}"
                else:
                    marker_color = 'red'
                    marker_symbol = 'triangle-down'
                    text = f"📉 OPTIMAL SHORT<br>Entry: ${entry_price:.2f}"

                fig.add_trace(
                    go.Scatter(
                        x=[timestamp],
                        y=[entry_price],
                        mode='markers',
                        marker=dict(
                            symbol=marker_symbol,
                            size=15,
                            color=marker_color,
                            line=dict(color='white', width=2)
                        ),
                        name=f'Optimal {trade["direction"]} Entry',
                        text=text,
                        hoverinfo='text',
                        showlegend=False
                    ),
                    row=row, col=1
                )

            # Exit signal
            exit_time = pd.to_datetime(trade['exit_time'])
            exit_price = trade['exit_price']

            time_diff = abs(df_viz['timestamp'] - exit_time)
            if time_diff.min() < pd.Timedelta(minutes=5):
                closest_idx = time_diff.idxmin()
                timestamp = df_viz.loc[closest_idx, 'timestamp']

                # Exit marker (opposite color)
                if trade['direction'].upper() == 'LONG':
                    exit_color = 'orange'
                    exit_symbol = 'triangle-down'
                    pnl_pct = trade.get('pnl_pct', 0)
                    text = f"🔻 OPTIMAL LONG EXIT<br>Exit: ${exit_price:.2f}<br>PnL: {pnl_pct:+.2f}%"
                else:
                    exit_color = 'cyan'
                    exit_symbol = 'triangle-up'
                    pnl_pct = trade.get('pnl_pct', 0)
                    text = f"🔺 OPTIMAL SHORT EXIT<br>Exit: ${exit_price:.2f}<br>PnL: {pnl_pct:+.2f}%"

                fig.add_trace(
                    go.Scatter(
                        x=[timestamp],
                        y=[exit_price],
                        mode='markers',
                        marker=dict(
                            symbol=exit_symbol,
                            size=15,
                            color=exit_color,
                            line=dict(color='white', width=2)
                        ),
                        name=f'Optimal {trade["direction"]} Exit',
                        text=text,
                        hoverinfo='text',
                        showlegend=False
                    ),
                    row=row, col=1
                )

    def _add_actual_trades(self, fig, df_viz, row=1):
        """Add actual trade signals from Claude decisions"""
        print("📍 Adding actual trade signals...")

        # Filter decisions to visualization timeframe
        decisions_viz = self.decisions[
            (self.decisions['timestamp'] >= df_viz['timestamp'].min()) &
            (self.decisions['timestamp'] <= df_viz['timestamp'].max())
        ].copy()

        # Find entries and exits
        for idx, decision in decisions_viz.iterrows():
            action = decision.get('action_type', 'decision')
            entry_rec = str(decision.get('entry_recommended', 'NO')).upper()
            direction = decision.get('direction', 'UNKNOWN').upper()
            executed = decision.get('executed', False)

            # Skip non-executed trades
            if not executed or pd.isna(executed):
                continue

            timestamp = decision['timestamp']
            price = decision.get('entry_price', 0)

            if pd.isna(price) or price == 0:
                continue

            # Find closest data point
            time_diff = abs(df_viz['timestamp'] - timestamp)
            if time_diff.min() < pd.Timedelta(minutes=5):
                closest_idx = time_diff.idxmin()
                viz_timestamp = df_viz.loc[closest_idx, 'timestamp']
                viz_price = df_viz.loc[closest_idx, 'price']

                # Entry markers
                if 'ENTRY' in entry_rec or action == 'entry':
                    if direction == 'LONG':
                        marker_color = 'green'
                        marker_symbol = 'circle'
                        text = f"✅ ACTUAL LONG<br>Entry: ${price:.2f}"
                    else:
                        marker_color = 'darkred'
                        marker_symbol = 'circle'
                        text = f"✅ ACTUAL SHORT<br>Entry: ${price:.2f}"

                    fig.add_trace(
                        go.Scatter(
                            x=[viz_timestamp],
                            y=[viz_price],
                            mode='markers',
                            marker=dict(
                                symbol=marker_symbol,
                                size=12,
                                color=marker_color,
                                line=dict(color='yellow', width=2)
                            ),
                            name=f'Actual {direction} Entry',
                            text=text,
                            hoverinfo='text',
                            showlegend=False
                        ),
                        row=row, col=1
                    )

                # Exit markers
                elif action == 'exit':
                    exit_price = decision.get('exit_price', price)
                    pnl = decision.get('pnl_dollars', 0)

                    if direction == 'LONG':
                        exit_color = 'lightgreen'
                        text = f"🟢 ACTUAL LONG EXIT<br>Exit: ${exit_price:.2f}<br>PnL: ${pnl:+.2f}"
                    else:
                        exit_color = 'pink'
                        text = f"🔴 ACTUAL SHORT EXIT<br>Exit: ${exit_price:.2f}<br>PnL: ${pnl:+.2f}"

                    fig.add_trace(
                        go.Scatter(
                            x=[viz_timestamp],
                            y=[viz_price],
                            mode='markers',
                            marker=dict(
                                symbol='x',
                                size=12,
                                color=exit_color,
                                line=dict(color='yellow', width=2)
                            ),
                            name=f'Actual {direction} Exit',
                            text=text,
                            hoverinfo='text',
                            showlegend=False
                        ),
                        row=row, col=1
                    )

    def _add_backtest_trades(self, fig, df_viz, row=1):
        """Add backtest trade entry/exit markers"""
        print("📍 Adding backtest trade signals...")

        for trade in self.backtest_trades:
            # Entry signal
            entry_time = pd.to_datetime(trade['entry_time'])
            entry_price = trade['entry_price']

            # Find closest timestamp in data
            time_diff = abs(df_viz['timestamp'] - entry_time)
            if time_diff.min() < pd.Timedelta(minutes=5):
                closest_idx = time_diff.idxmin()
                timestamp = df_viz.loc[closest_idx, 'timestamp']

                # Square markers for backtest (distinct from optimal triangles and actual circles)
                confidence = trade.get('confidence', 0)
                if trade['direction'].upper() == 'LONG':
                    marker_color = '#00FF7F'  # Spring green
                    marker_symbol = 'square'
                    text = f"🔲 BACKTEST LONG<br>Entry: ${entry_price:.2f}<br>Confidence: {confidence:.0%}"
                else:
                    marker_color = '#FF1493'  # Deep pink
                    marker_symbol = 'square'
                    text = f"🔲 BACKTEST SHORT<br>Entry: ${entry_price:.2f}<br>Confidence: {confidence:.0%}"

                fig.add_trace(
                    go.Scatter(
                        x=[timestamp],
                        y=[entry_price],
                        mode='markers',
                        marker=dict(
                            symbol=marker_symbol,
                            size=13,
                            color=marker_color,
                            line=dict(color='white', width=2)
                        ),
                        name=f'Backtest {trade["direction"]} Entry',
                        text=text,
                        hoverinfo='text',
                        showlegend=False
                    ),
                    row=row, col=1
                )

            # Exit signal
            exit_time = pd.to_datetime(trade['exit_time'])
            exit_price = trade['exit_price']

            time_diff = abs(df_viz['timestamp'] - exit_time)
            if time_diff.min() < pd.Timedelta(minutes=5):
                closest_idx = time_diff.idxmin()
                timestamp = df_viz.loc[closest_idx, 'timestamp']

                # Exit marker (diamond shape)
                if trade['direction'].upper() == 'LONG':
                    exit_color = '#98FB98'  # Pale green
                    exit_symbol = 'diamond'
                    pnl_pct = trade.get('pnl_pct', 0)
                    exit_reason = trade.get('exit_reason', 'Rule-based exit')
                    text = f"💎 BACKTEST LONG EXIT<br>Exit: ${exit_price:.2f}<br>PnL: {pnl_pct:+.2f}%<br>{exit_reason}"
                else:
                    exit_color = '#FFB6C1'  # Light pink
                    exit_symbol = 'diamond'
                    pnl_pct = trade.get('pnl_pct', 0)
                    exit_reason = trade.get('exit_reason', 'Rule-based exit')
                    text = f"💎 BACKTEST SHORT EXIT<br>Exit: ${exit_price:.2f}<br>PnL: {pnl_pct:+.2f}%<br>{exit_reason}"

                fig.add_trace(
                    go.Scatter(
                        x=[timestamp],
                        y=[exit_price],
                        mode='markers',
                        marker=dict(
                            symbol=exit_symbol,
                            size=13,
                            color=exit_color,
                            line=dict(color='white', width=2)
                        ),
                        name=f'Backtest {trade["direction"]} Exit',
                        text=text,
                        hoverinfo='text',
                        showlegend=False
                    ),
                    row=row, col=1
                )

    def calculate_slope_linear_regression(self, values, timestamps, lookback=10):
        """
        Calculate slope using linear regression (same as bot's EMADerivativeAnalyzer)

        Args:
            values: Pandas Series of EMA values
            timestamps: Pandas Series of timestamps
            lookback: Number of periods to use for regression

        Returns:
            List of slopes in price units per second
        """
        slopes = []

        for i in range(len(values)):
            # Get last N points
            start_idx = max(0, i - lookback + 1)
            val_window = values.iloc[start_idx:i+1].values
            time_window = timestamps.iloc[start_idx:i+1]

            if len(val_window) < 2:
                slopes.append(0.0)
                continue

            # Convert timestamps to seconds from first timestamp
            t_seconds = [(t - time_window.iloc[0]).total_seconds() for t in time_window]

            # Linear regression: slope = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
            n = len(val_window)
            sum_x = sum(t_seconds)
            sum_y = sum(val_window)
            sum_xy = sum(x * y for x, y in zip(t_seconds, val_window))
            sum_x2 = sum(x * x for x in t_seconds)

            denominator = n * sum_x2 - sum_x * sum_x
            if denominator == 0:
                slopes.append(0.0)
                continue

            slope = (n * sum_xy - sum_x * sum_y) / denominator
            slopes.append(slope)

        return slopes

    def _add_derivative_slopes(self, fig, df_viz, row=2):
        """Add derivative slope visualization using linear regression"""
        print("📈 Adding derivative slopes (linear regression method)...")

        fast_emas = [5, 10, 15, 20]
        slopes_found = False

        # Store slopes for inflection detection
        self._calculated_slopes = {}

        for ema in fast_emas:
            value_col = f'MMA{ema}_value'

            if value_col not in df_viz.columns:
                print(f"   ⚠️  {value_col} not in data")
                continue

            # Calculate slope using linear regression
            ema_values = df_viz[value_col].copy()
            timestamps = df_viz['timestamp']

            slopes = self.calculate_slope_linear_regression(ema_values, timestamps, lookback=10)
            slopes = pd.Series(slopes, index=df_viz.index)

            # Store for inflection detection
            self._calculated_slopes[ema] = slopes

            # Check if we have actual slope data
            if slopes.abs().sum() == 0:
                print(f"   ⚠️  MMA{ema} slope is all zeros")
                continue

            slopes_found = True

            # Color by EMA
            if ema == 5:
                color = 'cyan'
                name = 'EMA5 Slope (Fastest)'
            elif ema == 10:
                color = 'lightblue'
                name = 'EMA10 Slope'
            elif ema == 15:
                color = 'lightgreen'
                name = 'EMA15 Slope'
            else:
                color = 'yellow'
                name = 'EMA20 Slope'

            fig.add_trace(
                go.Scatter(
                    x=df_viz['timestamp'],
                    y=slopes,
                    name=name,
                    line=dict(
                        color=color,
                        width=2,
                        shape='spline',
                        smoothing=0.5
                    ),
                    mode='lines',
                    legendgroup='slopes',
                    showlegend=True
                ),
                row=row, col=1
            )

            print(f"   ✅ Added {name} (range: {slopes.min():.6f} to {slopes.max():.6f})")

        if not slopes_found:
            print("   ⚠️  No slope data available - run bot to collect derivative data!")
            # Add placeholder text
            fig.add_annotation(
                text="No derivative data yet - run bot to collect",
                xref=f"x{row}", yref=f"y{row}",
                x=df_viz['timestamp'].iloc[len(df_viz)//2],
                y=0,
                showarrow=False,
                font=dict(size=14, color="yellow"),
                row=row, col=1
            )
        else:
            # Add zero line only if we have data
            fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5, row=row, col=1)

    def calculate_compression_state(self, df_viz):
        """
        Calculate EMA compression state from EMA values

        Compression = coefficient of variation (std / mean) * 100
        Lower = more compressed (EMAs tight together)
        Higher = more expanded (EMAs spread apart)
        """
        print("📊 Calculating compression state from EMA values...")

        # Get all EMA value columns
        ema_cols = [col for col in df_viz.columns if col.startswith('MMA') and col.endswith('_value')]

        if not ema_cols:
            print("   ⚠️  No EMA value columns found")
            return None

        compressions = []

        for idx in range(len(df_viz)):
            ema_values = []

            for col in ema_cols:
                val = df_viz[col].iloc[idx]
                if pd.notna(val) and val != 'N/A':
                    try:
                        ema_values.append(float(val))
                    except:
                        pass

            if len(ema_values) > 1:
                mean_ema = np.mean(ema_values)
                std_ema = np.std(ema_values)

                # Compression = (std / mean) * 100
                if mean_ema > 0:
                    compression = (std_ema / mean_ema) * 100
                else:
                    compression = 0.0
            else:
                compression = 0.0

            compressions.append(compression)

        print(f"   ✅ Calculated compression (range: {min(compressions):.4f}% to {max(compressions):.4f}%)")

        return compressions

    def _add_compression_state(self, fig, df_viz, row=3):
        """Add compression state visualization"""
        print("📊 Adding compression state...")

        # Try to get from existing columns first
        if 'compression_value' in df_viz.columns:
            compression = df_viz['compression_value'].copy()
            print("   ✅ Using existing compression data from CSV")
        else:
            # Calculate on-the-fly
            compression = self.calculate_compression_state(df_viz)
            if compression is None:
                print("   ⚠️  Could not calculate compression")
                return
            compression = pd.Series(compression, index=df_viz.index)

        fig.add_trace(
            go.Scatter(
                x=df_viz['timestamp'],
                y=compression,
                name='Compression %',
                line=dict(color='orange', width=2, shape='spline', smoothing=0.3),
                fill='tozeroy',
                fillcolor='rgba(255, 165, 0, 0.3)',
                hovertemplate='Compression: %{y:.4f}%<extra></extra>'
            ),
            row=row, col=1
        )

        # Add threshold lines
        fig.add_hline(y=0.1, line_dash="dash", line_color="red", opacity=0.5,
                     annotation_text="Highly Compressed (0.1%)", row=row, col=1)
        fig.add_hline(y=0.2, line_dash="dash", line_color="yellow", opacity=0.5,
                     annotation_text="Compressed (0.2%)", row=row, col=1)
        fig.add_hline(y=0.8, line_dash="dash", line_color="green", opacity=0.5,
                     annotation_text="Expanding (0.8%)", row=row, col=1)

    def detect_inflection_signals(self, slopes_dict):
        """
        Detect inflection points from calculated slopes

        Args:
            slopes_dict: Dict of {ema_period: slopes_series}

        Returns:
            Dict with bullish/bearish inflection counts per timestamp
        """
        print("⚡ Detecting inflection points from slopes...")

        if not slopes_dict:
            return None

        # Get length from first slopes series
        length = len(list(slopes_dict.values())[0])

        bullish_inflections = [0] * length
        bearish_inflections = [0] * length
        bullish_accelerations = [0] * length
        bearish_accelerations = [0] * length

        for ema_period, slopes in slopes_dict.items():
            for i in range(3, len(slopes)):
                recent_slopes = slopes.iloc[i-2:i+1].values

                if len(recent_slopes) < 3:
                    continue

                # Bullish inflection: was falling, now rising
                if recent_slopes[0] < 0 and recent_slopes[1] < 0 and recent_slopes[2] > 0:
                    bullish_inflections[i] += 1

                # Bearish inflection: was rising, now falling
                elif recent_slopes[0] > 0 and recent_slopes[1] > 0 and recent_slopes[2] < 0:
                    bearish_inflections[i] += 1

                # Bullish acceleration: rising and getting steeper
                elif all(s > 0 for s in recent_slopes):
                    if recent_slopes[2] > recent_slopes[1] > recent_slopes[0]:
                        bullish_accelerations[i] += 1

                # Bearish acceleration: falling and getting steeper
                elif all(s < 0 for s in recent_slopes):
                    if recent_slopes[2] < recent_slopes[1] < recent_slopes[0]:
                        bearish_accelerations[i] += 1

        print(f"   ✅ Detected inflections (max bullish: {max(bullish_inflections)}, max bearish: {max(bearish_inflections)})")

        return {
            'bullish_inflections': bullish_inflections,
            'bearish_inflections': bearish_inflections,
            'bullish_accelerations': bullish_accelerations,
            'bearish_accelerations': bearish_accelerations
        }

    def _add_inflection_signals(self, fig, df_viz, row=4):
        """Add inflection signal indicators"""
        print("⚡ Adding inflection signals...")

        # Try to get from existing columns first
        if 'inflection_signal_strength' in df_viz.columns:
            bullish_strength = df_viz.get('bullish_inflections', 0) + df_viz.get('bullish_accelerations', 0)
            bearish_strength = df_viz.get('bearish_inflections', 0) + df_viz.get('bearish_accelerations', 0)
            print("   ✅ Using existing inflection data from CSV")
        else:
            # Calculate from slopes if we have them stored
            if not hasattr(self, '_calculated_slopes'):
                print("   ⚠️  No slope data to detect inflections from")
                return

            signals = self.detect_inflection_signals(self._calculated_slopes)
            if signals is None:
                print("   ⚠️  Could not detect inflections")
                return

            bullish_strength = pd.Series(
                [signals['bullish_inflections'][i] + signals['bullish_accelerations'][i]
                 for i in range(len(signals['bullish_inflections']))],
                index=df_viz.index
            )
            bearish_strength = pd.Series(
                [signals['bearish_inflections'][i] + signals['bearish_accelerations'][i]
                 for i in range(len(signals['bearish_inflections']))],
                index=df_viz.index
            )

        if isinstance(bullish_strength, pd.Series):
            fig.add_trace(
                go.Scatter(
                    x=df_viz['timestamp'],
                    y=bullish_strength,
                    name='Bullish Signals',
                    line=dict(color='lime', width=2, shape='spline', smoothing=0.3),
                    fill='tozeroy',
                    fillcolor='rgba(0, 255, 0, 0.3)',
                    hovertemplate='Bullish: %{y} signals<extra></extra>'
                ),
                row=row, col=1
            )

        if isinstance(bearish_strength, pd.Series):
            fig.add_trace(
                go.Scatter(
                    x=df_viz['timestamp'],
                    y=-bearish_strength,  # Negative for visual separation
                    name='Bearish Signals',
                    line=dict(color='red', width=2, shape='spline', smoothing=0.3),
                    fill='tozeroy',
                    fillcolor='rgba(255, 0, 0, 0.3)',
                    hovertemplate='Bearish: %{y} signals<extra></extra>'
                ),
                row=row, col=1
            )

        # Add threshold line
        fig.add_hline(y=2, line_dash="dash", line_color="white", opacity=0.3,
                     annotation_text="Signal Threshold (2+)", row=row, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="white", opacity=0.3, row=row, col=1)

    def save_html(self, fig, filename='trading_analysis.html'):
        """Save visualization as HTML"""
        output_path = f'trading_data/{filename}'
        fig.write_html(output_path)
        print(f"\n💾 Saved visualization to: {output_path}")
        print(f"📂 Open in browser: file://{output_path}")
        return output_path

    def show(self, fig):
        """Show visualization in browser"""
        fig.show()


def main():
    """Run visualization"""
    print("="*80)
    print("🎨 TRADING ANALYSIS VISUALIZATION")
    print("="*80)

    # Initialize visualizer
    viz = TradingVisualizer()

    # Load data
    if not viz.load_data():
        print("\n❌ Failed to load data files")
        return

    # Create visualization
    print("\n" + "="*80)
    print("Creating Interactive Chart...")
    print("="*80)

    # Create chart for last 12 hours with all 28 EMAs
    fig = viz.create_visualization(hours_back=12, show_all_emas=True)

    if fig is None:
        print("❌ Failed to create visualization")
        return

    # Save to HTML
    output_file = viz.save_html(fig, 'trading_analysis.html')

    print("\n" + "="*80)
    print("✅ VISUALIZATION COMPLETE!")
    print("="*80)

    print("""
CHART FEATURES:
1. 📈 Price line with all key EMAs (color-coded)
2. 📍 Optimal trade signals (bright triangles - best possible)
3. 🔲 Backtest trade signals (squares - current rules)
4. ⭕ Actual trade signals (circles - bot executed)
5. 📊 Derivative slopes for fast EMAs (MMA5, 10, 15, 20)
6. 🔵 Compression state (orange area chart)
7. ⚡ Inflection signals (bullish green, bearish red)

LEGEND:
Optimal Trades (Perfect Hindsight):
- 🔺 Lime triangle UP = Optimal LONG entry
- 🔻 Red triangle DOWN = Optimal SHORT entry
- 🔻 Orange triangle DOWN = Optimal LONG exit
- 🔺 Cyan triangle UP = Optimal SHORT exit

Backtest Trades (Current Algorithm):
- 🔲 Spring green square = Backtest LONG entry
- 🔲 Deep pink square = Backtest SHORT entry
- 💎 Pale green diamond = Backtest LONG exit
- 💎 Light pink diamond = Backtest SHORT exit

Actual Trades (Bot Executed):
- 🟢 Green circle = Actual LONG entry
- 🔴 Red circle = Actual SHORT entry
- ❌ Light green X = Actual LONG exit
- ❌ Pink X = Actual SHORT exit

DERIVATIVES:
- Cyan line = MMA5 slope (fastest)
- Light blue = MMA10 slope
- Light green = MMA15 slope
- Yellow = MMA20 slope

COMPRESSION:
- Below 0.1% = Highly compressed (breakout imminent)
- 0.1-0.2% = Compressed (tight range)
- 0.2-0.8% = Normal to expanding
- Above 0.8% = Highly expanded (strong trend)

INFLECTION SIGNALS:
- Green area (positive) = Bullish inflections/accelerations
- Red area (negative) = Bearish inflections/accelerations
- Above/below 2 = Strong signal (2+ inflections)

INTERACTION:
- Hover over any point to see details
- Zoom with mouse wheel or box select
- Pan by clicking and dragging
- Double-click to reset view
- Click legend items to hide/show traces
    """)

    print(f"\n🌐 Opening in browser...")
    print(f"   File: {output_file}")

    # Show in browser
    viz.show(fig)


if __name__ == '__main__':
    main()
