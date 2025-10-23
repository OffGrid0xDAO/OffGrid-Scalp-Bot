#!/usr/bin/env python3
"""
Live Trading Dashboard with EMA Ribbons

Creates a live-updating chart that refreshes every minute showing:
- Price candlesticks
- EMA ribbons (colored by position relative to price)
- Entry/exit signals
- Current position status
- Real-time updates

Run: python3 live_chart_dashboard.py
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser
from threading import Thread

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from data.hyperliquid_fetcher import HyperliquidFetcher
from strategy.entry_detector_user_pattern import EntryDetector
from dotenv import load_dotenv

# Load environment
load_dotenv()


class LiveChartDashboard:
    def __init__(self, symbol='ETH', timeframe='15m', update_interval=60):
        """
        Initialize live dashboard

        Args:
            symbol: Trading symbol
            timeframe: Chart timeframe
            update_interval: Update frequency in seconds
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.update_interval = update_interval
        self.fetcher = HyperliquidFetcher()
        self.entry_detector = EntryDetector()

        # EMA periods to display
        self.ema_periods = [5, 8, 13, 21, 34, 55, 89, 144]

        self.html_file = Path(__file__).parent / 'live_dashboard.html'

        print("="*80)
        print("📊 LIVE TRADING DASHBOARD")
        print("="*80)
        print(f"Symbol: {symbol}")
        print(f"Timeframe: {timeframe}")
        print(f"Update Interval: {update_interval}s")
        print(f"Dashboard URL: file://{self.html_file.absolute()}")
        print()
        print("The chart will update automatically every minute.")
        print("Press Ctrl+C to stop.")
        print("="*80)
        print()

    def calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all EMAs"""
        for period in self.ema_periods:
            df[f'EMA_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        return df

    def get_ema_color(self, ema_value: float, price: float) -> str:
        """Get EMA color based on position relative to price"""
        if ema_value < price:
            # Support (below price) = Green
            return 'rgba(0, 255, 0, 0.3)'
        else:
            # Resistance (above price) = Red
            return 'rgba(255, 0, 0, 0.3)'

    def fetch_data(self) -> pd.DataFrame:
        """Fetch latest data from Hyperliquid"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching data...")

        # Fetch historical data (last 7 days for EMA stability)
        candles = self.fetcher.fetch_historical_data(
            interval=self.timeframe,
            days_back=7,
            use_checkpoint=False  # Always fetch fresh data
        )

        # Convert to DataFrame
        df = pd.DataFrame(candles)
        # Rename columns to standard names
        df = df.rename(columns={
            't': 'timestamp',
            'o': 'open',
            'c': 'close',
            'h': 'high',
            'l': 'low',
            'v': 'volume'
        })
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Calculate EMAs
        df = self.calculate_emas(df)

        # Get 5m data for signal
        candles_5m = self.fetcher.fetch_historical_data(
            interval='5m',
            days_back=1,
            use_checkpoint=False
        )

        df_5m = pd.DataFrame(candles_5m)
        df_5m = df_5m.rename(columns={
            't': 'timestamp',
            'o': 'open',
            'c': 'close',
            'h': 'high',
            'l': 'low',
            'v': 'volume'
        })
        df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'], unit='ms')
        df_5m = df_5m.sort_values('timestamp').reset_index(drop=True)

        # Get signal
        signal = self.entry_detector.detect_entry(df, df_5m)

        return df, signal

    def create_chart(self, df: pd.DataFrame, signal: dict) -> go.Figure:
        """Create Plotly chart with EMA ribbons"""

        # Show last 200 candles for better visibility
        df_display = df.tail(200).copy()

        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{self.symbol} - {self.timeframe} with EMA Ribbons', 'Volume'),
            vertical_spacing=0.05,
            shared_xaxes=True
        )

        # Candlesticks
        fig.add_trace(
            go.Candlestick(
                x=df_display['timestamp'],
                open=df_display['open'],
                high=df_display['high'],
                low=df_display['low'],
                close=df_display['close'],
                name='Price',
                increasing_line_color='#26A69A',
                decreasing_line_color='#EF5350'
            ),
            row=1, col=1
        )

        # EMA Ribbons (fill between consecutive EMAs)
        current_price = df_display['close'].iloc[-1]

        for i in range(len(self.ema_periods) - 1):
            period1 = self.ema_periods[i]
            period2 = self.ema_periods[i + 1]

            ema1_values = df_display[f'EMA_{period1}']
            ema2_values = df_display[f'EMA_{period2}']

            # Determine ribbon color based on average position
            avg_ema = (ema1_values.iloc[-1] + ema2_values.iloc[-1]) / 2

            if avg_ema < current_price:
                # Support (green)
                color = f'rgba(0, 255, 0, {0.15 + (i * 0.05)})'
            else:
                # Resistance (red)
                color = f'rgba(255, 0, 0, {0.15 + (i * 0.05)})'

            # Add filled area between EMAs
            fig.add_trace(
                go.Scatter(
                    x=df_display['timestamp'],
                    y=ema1_values,
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo='skip'
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df_display['timestamp'],
                    y=ema2_values,
                    mode='lines',
                    line=dict(width=0),
                    fill='tonexty',
                    fillcolor=color,
                    name=f'EMA {period1}-{period2}',
                    showlegend=(i == 0)  # Only show first in legend
                ),
                row=1, col=1
            )

        # Add EMA lines (visible ones)
        for period in [5, 21, 55, 144]:  # Key EMAs
            fig.add_trace(
                go.Scatter(
                    x=df_display['timestamp'],
                    y=df_display[f'EMA_{period}'],
                    mode='lines',
                    name=f'EMA {period}',
                    line=dict(width=1.5),
                    opacity=0.8
                ),
                row=1, col=1
            )

        # Volume bars
        colors = ['#26A69A' if close >= open else '#EF5350'
                 for close, open in zip(df_display['close'], df_display['open'])]

        fig.add_trace(
            go.Bar(
                x=df_display['timestamp'],
                y=df_display['volume'],
                name='Volume',
                marker_color=colors,
                showlegend=False
            ),
            row=2, col=1
        )

        # Add signal markers if there's a valid signal
        if signal and signal.get('quality_score', 0) >= 50:
            latest_time = df_display['timestamp'].iloc[-1]
            latest_price = df_display['close'].iloc[-1]

            if signal['direction'] == 'long':
                marker_color = '#00FF00'
                marker_symbol = 'triangle-up'
                text = f"🚀 LONG<br>Quality: {signal['quality_score']:.0f}"
            else:
                marker_color = '#FF0000'
                marker_symbol = 'triangle-down'
                text = f"🔻 SHORT<br>Quality: {signal['quality_score']:.0f}"

            fig.add_trace(
                go.Scatter(
                    x=[latest_time],
                    y=[latest_price],
                    mode='markers+text',
                    marker=dict(
                        size=20,
                        color=marker_color,
                        symbol=marker_symbol,
                        line=dict(width=2, color='white')
                    ),
                    text=text,
                    textposition='top center',
                    name='Signal',
                    showlegend=False
                ),
                row=1, col=1
            )

        # Update layout
        fig.update_layout(
            title=dict(
                text=f'{self.symbol} Live Chart - Last Update: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                x=0.5,
                xanchor='center'
            ),
            xaxis_rangeslider_visible=False,
            height=900,
            template='plotly_dark',
            hovermode='x unified',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

        return fig

    def update_chart(self):
        """Fetch data and update chart"""
        try:
            df, signal = self.fetch_data()

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Data fetched: {len(df)} candles")

            if signal:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Signal: {signal['direction'].upper()} "
                      f"(Quality: {signal.get('quality_score', 0):.0f})")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No qualifying signal")

            # Create chart
            fig = self.create_chart(df, signal)

            # Save to HTML with auto-refresh
            html_content = fig.to_html(include_plotlyjs='cdn')

            # Add auto-refresh meta tag
            html_content = html_content.replace(
                '<head>',
                f'<head><meta http-equiv="refresh" content="{self.update_interval}">'
            )

            with open(self.html_file, 'w') as f:
                f.write(html_content)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Chart updated successfully!")
            print()

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error updating chart: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Main loop - update chart periodically"""
        # Initial update
        self.update_chart()

        # Open browser
        webbrowser.open(f'file://{self.html_file.absolute()}')

        print("✅ Dashboard opened in browser!")
        print(f"Chart will refresh every {self.update_interval} seconds")
        print()

        # Update loop
        try:
            while True:
                time.sleep(self.update_interval)
                self.update_chart()

        except KeyboardInterrupt:
            print("\n" + "="*80)
            print("Dashboard stopped by user (Ctrl+C)")
            print("="*80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Live Trading Dashboard')
    parser.add_argument('--symbol', type=str, default='ETH',
                       help='Trading symbol (default: ETH)')
    parser.add_argument('--timeframe', type=str, default='15m',
                       help='Chart timeframe (default: 15m)')
    parser.add_argument('--interval', type=int, default=60,
                       help='Update interval in seconds (default: 60)')

    args = parser.parse_args()

    dashboard = LiveChartDashboard(
        symbol=args.symbol,
        timeframe=args.timeframe,
        update_interval=args.interval
    )

    dashboard.run()


if __name__ == "__main__":
    main()
