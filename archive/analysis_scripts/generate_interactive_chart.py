#!/usr/bin/env python3
"""
Generate Interactive HTML Chart

Creates a beautiful interactive chart with Plotly showing:
- Price action with candlesticks
- Entry and exit points
- Profit/loss for each trade
- RSI indicator
- Volume
- Hover information

Can be opened in browser for full interactivity!
"""

import pandas as pd
import numpy as np
import pickle
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime


print("\n" + "="*80)
print("📊 GENERATING INTERACTIVE HTML CHART")
print("="*80)

# Load backtest results
data_dir = Path(__file__).parent / 'trading_data'

print("\n📂 Loading backtest results...")
with open(data_dir / 'full_month_results.pkl', 'rb') as f:
    data = pickle.load(f)

df_signals = data['df_signals']
trades = data['trades']
results = data['results']

print(f"   Period: {results['period']['start']} to {results['period']['end']}")
print(f"   Total trades: {len(trades)}")
print(f"   Win rate: {results['trades']['win_rate']:.1f}%")
print(f"   Return: {results['capital']['return_pct']:+.2f}%")

# Create subplots
print("\n🎨 Creating interactive chart...")
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=('ETH/USD Price Action with Trades', 'RSI (14)', 'Volume'),
    row_heights=[0.6, 0.2, 0.2]
)

# 1. Candlestick chart
fig.add_trace(
    go.Candlestick(
        x=df_signals['timestamp'],
        open=df_signals['open'],
        high=df_signals['high'],
        low=df_signals['low'],
        close=df_signals['close'],
        name='ETH/USD',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ),
    row=1, col=1
)

# 2. Add entry points
for i, trade in enumerate(trades, 1):
    entry_time = pd.to_datetime(trade['entry_time'])
    entry_price = trade['entry_price']
    direction = trade['direction']

    # Entry marker
    if direction == 'long':
        marker_color = 'green'
        marker_symbol = 'triangle-up'
        marker_size = 15
    else:
        marker_color = 'red'
        marker_symbol = 'triangle-down'
        marker_size = 15

    fig.add_trace(
        go.Scatter(
            x=[entry_time],
            y=[entry_price],
            mode='markers',
            name=f'Entry #{i} {direction.upper()}',
            marker=dict(
                color=marker_color,
                size=marker_size,
                symbol=marker_symbol,
                line=dict(color='white', width=2)
            ),
            hovertemplate=(
                f"<b>ENTRY #{i}</b><br>" +
                f"Direction: {direction.upper()}<br>" +
                f"Price: ${entry_price:.2f}<br>" +
                f"Time: {entry_time}<br>" +
                f"Quality: {trade['quality_score']:.1f}<br>" +
                "<extra></extra>"
            ),
            showlegend=False
        ),
        row=1, col=1
    )

    # Exit marker
    exit_time = pd.to_datetime(trade['exit_time'])
    exit_price = trade['exit_price']
    profit_pct = trade['profit_pct']

    exit_color = 'lime' if profit_pct > 0 else 'orangered'

    fig.add_trace(
        go.Scatter(
            x=[exit_time],
            y=[exit_price],
            mode='markers',
            name=f'Exit #{i}',
            marker=dict(
                color=exit_color,
                size=12,
                symbol='x',
                line=dict(color='white', width=2)
            ),
            hovertemplate=(
                f"<b>EXIT #{i}</b><br>" +
                f"Reason: {trade['exit_reason']}<br>" +
                f"Price: ${exit_price:.2f}<br>" +
                f"Profit: {profit_pct:+.2f}%<br>" +
                f"P&L: ${trade['pnl']:+.2f}<br>" +
                f"Time: {exit_time}<br>" +
                "<extra></extra>"
            ),
            showlegend=False
        ),
        row=1, col=1
    )

    # Draw line from entry to exit
    fig.add_trace(
        go.Scatter(
            x=[entry_time, exit_time],
            y=[entry_price, exit_price],
            mode='lines',
            line=dict(
                color=exit_color,
                width=2,
                dash='dot'
            ),
            hoverinfo='skip',
            showlegend=False
        ),
        row=1, col=1
    )

    # Add profit/loss annotation
    mid_time = entry_time + (exit_time - entry_time) / 2
    mid_price = (entry_price + exit_price) / 2

    fig.add_annotation(
        x=mid_time,
        y=mid_price,
        text=f"{profit_pct:+.1f}%",
        showarrow=False,
        font=dict(size=10, color='white'),
        bgcolor=exit_color,
        opacity=0.8,
        bordercolor='white',
        borderwidth=1,
        row=1, col=1
    )

# 3. RSI indicator
if 'rsi_14' in df_signals.columns:
    fig.add_trace(
        go.Scatter(
            x=df_signals['timestamp'],
            y=df_signals['rsi_14'],
            mode='lines',
            name='RSI(14)',
            line=dict(color='purple', width=1.5)
        ),
        row=2, col=1
    )

    # RSI levels
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, row=2, col=1)

# 4. Volume
colors = ['green' if df_signals.iloc[i]['close'] >= df_signals.iloc[i]['open']
          else 'red' for i in range(len(df_signals))]

fig.add_trace(
    go.Bar(
        x=df_signals['timestamp'],
        y=df_signals['volume'],
        name='Volume',
        marker_color=colors,
        opacity=0.5
    ),
    row=3, col=1
)

# Update layout
fig.update_layout(
    title={
        'text': (
            f"<b>MTF Strategy Backtest - Full Month</b><br>" +
            f"<sub>{results['period']['start']} to {results['period']['end']} | " +
            f"{len(trades)} Trades | {results['trades']['win_rate']:.1f}% Win Rate | " +
            f"{results['capital']['return_pct']:+.2f}% Return</sub>"
        ),
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 20}
    },
    height=1000,
    showlegend=True,
    hovermode='x unified',
    template='plotly_dark',
    xaxis_rangeslider_visible=False,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

# Update axes
fig.update_xaxes(title_text="Date", row=3, col=1)
fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
fig.update_yaxes(title_text="Volume", row=3, col=1)

# Add trade summary annotations
summary_text = (
    f"<b>Performance Summary</b><br>"
    f"Trades: {len(trades)}<br>"
    f"Win Rate: {results['trades']['win_rate']:.1f}%<br>"
    f"Return: {results['capital']['return_pct']:+.2f}%<br>"
    f"P&L: ${results['capital']['pnl']:+.2f}<br>"
    f"Annualized: {results['capital']['return_pct'] * 12:+.1f}%"
)

fig.add_annotation(
    xref="paper", yref="paper",
    x=0.02, y=0.98,
    text=summary_text,
    showarrow=False,
    font=dict(size=11, color='white'),
    bgcolor='rgba(0,0,0,0.7)',
    bordercolor='white',
    borderwidth=1,
    align='left',
    xanchor='left',
    yanchor='top'
)

# Save to HTML
output_file = data_dir / 'charts' / 'interactive_full_month.html'
output_file.parent.mkdir(parents=True, exist_ok=True)

fig.write_html(str(output_file))

print(f"\n✅ Interactive chart generated!")
print(f"   📁 Saved to: {output_file}")
print(f"   🌐 Open in browser to interact with the chart")

# Also save a static PNG version
print("\n📸 Saving static PNG version...")
try:
    static_file = data_dir / 'charts' / 'full_month_trades.png'
    fig.write_image(str(static_file), width=1920, height=1080)
    print(f"   ✅ Saved to: {static_file}")
except Exception as e:
    print(f"   ⚠️  Could not save PNG (kaleido not installed): {e}")

print("\n" + "="*80)
print("✅ CHART GENERATION COMPLETE!")
print("="*80)

# Print trade details
print("\n📋 Trade Details:")
print("="*80)

for i, trade in enumerate(trades, 1):
    profit_symbol = "✅" if trade['profit_pct'] > 0 else "❌"
    print(f"\n{profit_symbol} Trade #{i}: {trade['direction'].upper()}")
    print(f"   Entry:  {trade['entry_time']} @ ${trade['entry_price']:.2f}")
    print(f"   Exit:   {trade['exit_time']} @ ${trade['exit_price']:.2f}")
    print(f"   Profit: {trade['profit_pct']:+.2f}% (${trade['pnl']:+.2f})")
    print(f"   Reason: {trade['exit_reason']}")
    print(f"   Peak:   {trade['peak_profit_pct']:.2f}%")

print("\n" + "="*80)
print(f"🌐 Open the chart: open {output_file}")
print("="*80)
