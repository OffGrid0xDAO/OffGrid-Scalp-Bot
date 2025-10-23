#!/usr/bin/env python3
"""
Create comprehensive charts for all timeframes

Multi-panel interactive charts showing:
- Panel 1: Price + EMA Ribbon + Bollinger Bands + VWAP
- Panel 2: Volume with status
- Panel 3: RSI (7 & 14)
- Panel 4: Stochastic Oscillator (5-3-3) - NEW!
- Panel 5: MACD (Fast & Standard)
- Panel 6: Confluence Score

Updated with professional day trading indicators for 2-3 trades/day strategy
"""

import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def create_comprehensive_chart(
    df: pd.DataFrame,
    timeframe: str,
    symbol: str = 'ETH',
    output_file: str = None,
    candles_to_show: int = None
):
    """
    Create comprehensive multi-panel chart

    Args:
        df: DataFrame with all indicators
        timeframe: Timeframe string (e.g., '5m', '1h')
        symbol: Trading symbol
        output_file: Output HTML file path
        candles_to_show: Number of most recent candles to show (None = all)
    """
    # Filter to recent candles if specified
    if candles_to_show:
        df = df.tail(candles_to_show)

    print(f"\n📊 Creating chart for {symbol} {timeframe}...")
    print(f"   Candles: {len(df)}")

    # Create subplot figure with 6 panels (added Stochastic)
    fig = make_subplots(
        rows=6, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.35, 0.13, 0.13, 0.13, 0.13, 0.13],
        subplot_titles=(
            f'{symbol} {timeframe} - Price + EMA Ribbon + Bollinger Bands + VWAP',
            'Volume',
            'RSI (7 & 14)',
            'Stochastic (5-3-3) - Professional Day Trading',
            'MACD (Fast & Standard)',
            'Confluence Score'
        )
    )

    # Panel 1: Candlesticks + EMAs + Bollinger Bands + VWAP
    _add_price_panel(fig, df, row=1)

    # Panel 2: Volume
    _add_volume_panel(fig, df, row=2)

    # Panel 3: RSI
    _add_rsi_panel(fig, df, row=3)

    # Panel 4: Stochastic (NEW!)
    _add_stochastic_panel(fig, df, row=4)

    # Panel 5: MACD
    _add_macd_panel(fig, df, row=5)

    # Panel 6: Confluence Score
    _add_confluence_panel(fig, df, row=6)

    # Update layout
    fig.update_layout(
        title=f'{symbol} {timeframe} - Professional Day Trading Analysis ({len(df)} candles)',
        xaxis_rangeslider_visible=False,
        height=1600,  # Increased for 6 panels
        showlegend=True,
        hovermode='x unified',
        template='plotly_dark',
        font=dict(size=10)
    )

    # Save to file
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        fig.write_html(output_file)
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"   ✅ Chart saved: {output_file} ({file_size:.1f} MB)")

    return fig


def _add_price_panel(fig, df, row):
    """Add price candlesticks + Full EMA Ribbon + Bollinger Bands + VWAP"""
    # Candlesticks
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            showlegend=True
        ),
        row=row, col=1
    )

    # Bollinger Bands (NEW!)
    if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
        # Lower band first
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

        # Middle band
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

    # VWAP
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

    # Full EMA Ribbon - All 35 EMAs with dynamic colors
    # Includes important crossover EMAs: 8, 9, 12, 21, 26, 95, 200
    ema_periods = [5, 8, 9, 10, 12, 15, 20, 21, 25, 26, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                  85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 200]  # 35 EMAs

    for period in ema_periods:
        ema_value_col = f'MMA{period}_value'
        ema_color_col = f'MMA{period}_color'

        if ema_value_col not in df.columns or ema_color_col not in df.columns:
            continue

        # Get dynamic colors for each candle (green when price > EMA, red when price < EMA)
        # Map 'neutral' to gray for visualization
        colors = df[ema_color_col].map(lambda x: 'gray' if x == 'neutral' else x).tolist()

        # Create segments for color changes
        # We'll plot each EMA as separate segments when color changes
        segments = []
        current_color = colors[0] if colors else 'green'
        start_idx = 0

        for i in range(1, len(colors)):
            if colors[i] != current_color or i == len(colors) - 1:
                # Add segment
                end_idx = i if i == len(colors) - 1 else i
                segments.append({
                    'start': start_idx,
                    'end': end_idx,
                    'color': current_color
                })
                current_color = colors[i]
                start_idx = i

        # Plot each segment with its color
        for seg_idx, seg in enumerate(segments):
            seg_df = df.iloc[seg['start']:seg['end']+1]

            # Determine line width: thicker for key EMAs (20, 50, 100, 200)
            width = 2 if period in [20, 50, 100, 145] else 1

            # Show legend only for first segment and only for key EMAs
            show_legend = (seg_idx == 0) and (period in [5, 20, 50, 100, 145])

            fig.add_trace(
                go.Scatter(
                    x=seg_df['timestamp'],
                    y=seg_df[ema_value_col],
                    name=f'EMA{period}' if show_legend else None,
                    line=dict(color=seg['color'], width=width),
                    showlegend=show_legend,
                    legendgroup=f'ema{period}',
                    hovertemplate=f'EMA{period}: %{{y:.2f}}<extra></extra>'
                ),
                row=row, col=1
            )


def _add_volume_panel(fig, df, row):
    """Add volume bars with status colors"""
    # Color bars based on volume status
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

    # Volume EMA
    if 'volume_ema' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['volume_ema'],
                name='Vol EMA',
                line=dict(color='yellow', width=1),
                showlegend=False
            ),
            row=row, col=1
        )


def _add_rsi_panel(fig, df, row):
    """Add RSI 7 & 14"""
    # RSI 7
    if 'rsi_7' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['rsi_7'],
                name='RSI 7',
                line=dict(color='cyan', width=1),
                showlegend=False
            ),
            row=row, col=1
        )

    # RSI 14
    if 'rsi_14' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['rsi_14'],
                name='RSI 14',
                line=dict(color='orange', width=2),
                showlegend=False
            ),
            row=row, col=1
        )

    # Overbought/Oversold lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=row, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=row, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="gray", opacity=0.3, row=row, col=1)


def _add_macd_panel(fig, df, row):
    """Add MACD Fast & Standard"""
    # MACD Fast Line
    if 'macd_fast_line' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['macd_fast_line'],
                name='MACD Fast',
                line=dict(color='cyan', width=1),
                showlegend=False
            ),
            row=row, col=1
        )

    # MACD Fast Signal
    if 'macd_fast_signal' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['macd_fast_signal'],
                name='Signal Fast',
                line=dict(color='orange', width=1, dash='dash'),
                showlegend=False
            ),
            row=row, col=1
        )

    # MACD Fast Histogram
    if 'macd_fast_histogram' in df.columns:
        colors = ['green' if x > 0 else 'red' for x in df['macd_fast_histogram']]
        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['macd_fast_histogram'],
                name='MACD Hist',
                marker_color=colors,
                opacity=0.5,
                showlegend=False
            ),
            row=row, col=1
        )

    # Zero line
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.3, row=row, col=1)


def _add_stochastic_panel(fig, df, row):
    """Add Stochastic Oscillator (5-3-3) - NEW! Professional day trading indicator"""
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


def _add_confluence_panel(fig, df, row):
    """Add confluence scores"""
    # Long score (green)
    if 'confluence_score_long' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['confluence_score_long'],
                name='Long Score',
                line=dict(color='green', width=1),
                fill='tozeroy',
                fillcolor='rgba(0,255,0,0.1)',
                showlegend=False
            ),
            row=row, col=1
        )

    # Short score (red)
    if 'confluence_score_short' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['confluence_score_short'],
                name='Short Score',
                line=dict(color='red', width=1),
                fill='tozeroy',
                fillcolor='rgba(255,0,0,0.1)',
                showlegend=False
            ),
            row=row, col=1
        )

    # Entry threshold line (70)
    fig.add_hline(y=70, line_dash="dash", line_color="yellow", opacity=0.5, row=row, col=1)


def process_all_timeframes():
    """Create charts for all timeframes"""
    print("="*80)
    print("CREATING CHARTS FOR ALL TIMEFRAMES")
    print("="*80)

    timeframes = ['1m', '3m', '5m', '15m', '30m', '1h']
    symbol = 'eth'
    input_dir = 'trading_data/indicators'
    output_dir = 'charts/comprehensive'

    for tf in timeframes:
        input_file = f'{input_dir}/{symbol}_{tf}_full.csv'
        output_file = f'{output_dir}/{symbol}_{tf}_comprehensive.html'

        if not os.path.exists(input_file):
            print(f"\n⚠️  Skipping {tf} - file not found")
            continue

        print(f"\n{'='*80}")
        print(f"Processing {tf} timeframe")
        print(f"{'='*80}")

        try:
            # Load data
            df = pd.read_csv(input_file)

            # Create chart (show ALL historical data)
            create_comprehensive_chart(
                df=df,
                timeframe=tf,
                symbol=symbol.upper(),
                output_file=output_file,
                candles_to_show=None  # None = show all data
            )

        except Exception as e:
            print(f"\n❌ Error creating chart for {tf}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print("✅ ALL CHARTS CREATED")
    print(f"{'='*80}")
    print(f"\n📂 Charts directory: {output_dir}/")


if __name__ == '__main__':
    process_all_timeframes()
