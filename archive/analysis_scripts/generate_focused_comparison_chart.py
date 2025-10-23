#!/usr/bin/env python3
"""
Generate Interactive Chart: Bot Trades vs User Trades (Focused Period)
Shows 15m chart with both bot and user entries/exits
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import timedelta

print("\n🎨 Generating Comparison Chart: Bot vs User Trades (Oct 5-21)")

# Load data
data_dir = Path(__file__).parent / 'trading_data'
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

# Filter to focused period
start_date = pd.Timestamp('2025-10-05')
end_date = pd.Timestamp('2025-10-22')
df_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()

# Load user's trades
with open(data_dir / 'optimal_trades.json', 'r') as f:
    user_data = json.load(f)
user_trades = user_data['optimal_entries']

# Parse user trades
user_entries_long = []
user_entries_short = []
user_exits = []

for trade in user_trades:
    entry_time = pd.to_datetime(trade['timestamp'])
    exit_time = pd.to_datetime(trade['exit_timestamp'])
    direction = trade['direction']

    # Find nearest 15m candle for price
    tolerance = timedelta(minutes=1)
    entry_candle = df_period[
        (df_period['timestamp'] >= entry_time - tolerance) &
        (df_period['timestamp'] <= entry_time + tolerance)
    ]
    exit_candle = df_period[
        (df_period['timestamp'] >= exit_time - tolerance) &
        (df_period['timestamp'] <= exit_time + tolerance)
    ]

    if len(entry_candle) > 0:
        entry_price = entry_candle.iloc[0]['close']
        if direction == 'long':
            user_entries_long.append({'time': entry_time, 'price': entry_price})
        else:
            user_entries_short.append({'time': entry_time, 'price': entry_price})

        if len(exit_candle) > 0:
            exit_price = exit_candle.iloc[0]['close']
            user_exits.append({
                'entry_time': entry_time,
                'exit_time': exit_time,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'direction': direction
            })

# Load bot trades (from 15m backtest - we'll need to re-run and save)
# For now, let's re-run the 15m backtest and collect trades
import sys
sys.path.append(str(Path(__file__).parent / 'src'))
from strategy.entry_detector_user_pattern import EntryDetector
from strategy.exit_manager_user_pattern import ExitManager

# Run bot backtest
df_5m = pd.read_csv(data_dir / 'indicators' / 'eth_5m_full.csv')
df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'])
df_5m_period = df_5m[(df_5m['timestamp'] >= start_date) & (df_5m['timestamp'] < end_date)].copy()

detector = EntryDetector(df_5m=df_5m_period, df_15m=df_period)
df_signals = detector.scan_historical_signals(df_period)

exit_manager = ExitManager()
capital = 1000.0
bot_trades = []
in_position = False
current_trade = None

for i in range(len(df_signals)):
    row = df_signals.iloc[i]

    if not in_position and row['entry_signal']:
        current_trade = {
            'entry_time': row['timestamp'],
            'entry_price': row['close'],
            'direction': row['entry_direction'],
            'peak_profit_pct': 0.0,
        }
        in_position = True

    elif in_position and current_trade:
        if current_trade['direction'] == 'long':
            profit_pct = (row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
        else:
            profit_pct = (current_trade['entry_price'] - row['close']) / current_trade['entry_price'] * 100

        current_trade['peak_profit_pct'] = max(current_trade['peak_profit_pct'], profit_pct)

        exit_result = exit_manager.check_exit(
            current_trade['entry_price'],
            current_trade['entry_time'],
            row['close'],
            row['timestamp'],
            current_trade['direction'],
            current_trade['peak_profit_pct']
        )

        if exit_result['should_exit']:
            current_trade['exit_time'] = row['timestamp']
            current_trade['exit_price'] = exit_result['exit_price']
            current_trade['profit_pct'] = exit_result['profit_pct']

            bot_trades.append(current_trade)
            in_position = False
            current_trade = None

# Close final position if needed
if in_position and current_trade:
    last_row = df_signals.iloc[-1]
    if current_trade['direction'] == 'long':
        profit_pct = (last_row['close'] - current_trade['entry_price']) / current_trade['entry_price'] * 100
    else:
        profit_pct = (current_trade['entry_price'] - last_row['close']) / current_trade['entry_price'] * 100

    current_trade['exit_time'] = last_row['timestamp']
    current_trade['exit_price'] = last_row['close']
    current_trade['profit_pct'] = profit_pct
    bot_trades.append(current_trade)

print(f"📊 Chart data collected:")
print(f"   User: {len(user_entries_long)} longs, {len(user_entries_short)} shorts")
print(f"   Bot: {len(bot_trades)} total trades")

# Create chart
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=('Price & Trades', 'RSI-7', 'Volume'),
    row_heights=[0.6, 0.2, 0.2]
)

# Main price chart (candlesticks)
fig.add_trace(
    go.Candlestick(
        x=df_period['timestamp'],
        open=df_period['open'],
        high=df_period['high'],
        low=df_period['low'],
        close=df_period['close'],
        name='ETH/USDT 15m',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ),
    row=1, col=1
)

# USER TRADES (Green/Red markers - larger)
if user_entries_long:
    fig.add_trace(
        go.Scatter(
            x=[t['time'] for t in user_entries_long],
            y=[t['price'] for t in user_entries_long],
            mode='markers',
            name='👤 User LONG',
            marker=dict(
                symbol='triangle-up',
                size=20,
                color='lime',
                line=dict(color='darkgreen', width=2)
            )
        ),
        row=1, col=1
    )

if user_entries_short:
    fig.add_trace(
        go.Scatter(
            x=[t['time'] for t in user_entries_short],
            y=[t['price'] for t in user_entries_short],
            mode='markers',
            name='👤 User SHORT',
            marker=dict(
                symbol='triangle-down',
                size=20,
                color='red',
                line=dict(color='darkred', width=2)
            )
        ),
        row=1, col=1
    )

# USER EXIT LINES
for exit_trade in user_exits:
    color = 'rgba(0,255,0,0.3)' if exit_trade['direction'] == 'long' else 'rgba(255,0,0,0.3)'
    fig.add_trace(
        go.Scatter(
            x=[exit_trade['entry_time'], exit_trade['exit_time']],
            y=[exit_trade['entry_price'], exit_trade['exit_price']],
            mode='lines',
            line=dict(color=color, width=2, dash='solid'),
            showlegend=False,
            hovertemplate=f"User {exit_trade['direction'].upper()}<br>" +
                         f"Entry: {exit_trade['entry_price']:.2f}<br>" +
                         f"Exit: {exit_trade['exit_price']:.2f}<extra></extra>"
        ),
        row=1, col=1
    )

# BOT TRADES (Blue/Orange markers - smaller)
bot_longs = [t for t in bot_trades if t['direction'] == 'long']
bot_shorts = [t for t in bot_trades if t['direction'] == 'short']

if bot_longs:
    fig.add_trace(
        go.Scatter(
            x=[t['entry_time'] for t in bot_longs],
            y=[t['entry_price'] for t in bot_longs],
            mode='markers',
            name='🤖 Bot LONG',
            marker=dict(
                symbol='triangle-up',
                size=12,
                color='cyan',
                line=dict(color='blue', width=1)
            )
        ),
        row=1, col=1
    )

if bot_shorts:
    fig.add_trace(
        go.Scatter(
            x=[t['entry_time'] for t in bot_shorts],
            y=[t['entry_price'] for t in bot_shorts],
            mode='markers',
            name='🤖 Bot SHORT',
            marker=dict(
                symbol='triangle-down',
                size=12,
                color='orange',
                line=dict(color='darkorange', width=1)
            )
        ),
        row=1, col=1
    )

# BOT EXIT LINES (thinner, dashed)
for bot_trade in bot_trades:
    color = 'rgba(0,200,255,0.2)' if bot_trade['direction'] == 'long' else 'rgba(255,165,0,0.2)'
    fig.add_trace(
        go.Scatter(
            x=[bot_trade['entry_time'], bot_trade['exit_time']],
            y=[bot_trade['entry_price'], bot_trade['exit_price']],
            mode='lines',
            line=dict(color=color, width=1, dash='dot'),
            showlegend=False,
            hovertemplate=f"Bot {bot_trade['direction'].upper()}<br>" +
                         f"Entry: {bot_trade['entry_price']:.2f}<br>" +
                         f"Exit: {bot_trade['exit_price']:.2f}<br>" +
                         f"P&L: {bot_trade['profit_pct']:+.2f}%<extra></extra>"
        ),
        row=1, col=1
    )

# RSI-7 indicator
fig.add_trace(
    go.Scatter(
        x=df_period['timestamp'],
        y=df_period['rsi_7'],
        name='RSI-7',
        line=dict(color='purple', width=1)
    ),
    row=2, col=1
)

# RSI levels
fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

# Volume
colors = ['red' if row['close'] < row['open'] else 'green' for _, row in df_period.iterrows()]
fig.add_trace(
    go.Bar(
        x=df_period['timestamp'],
        y=df_period['volume'],
        name='Volume',
        marker_color=colors,
        opacity=0.5
    ),
    row=3, col=1
)

# Layout
fig.update_layout(
    title={
        'text': '🎯 Focused Period Comparison: Bot (🤖) vs User (👤) Trades<br>' +
                f'<sub>Period: Oct 5-21, 2025 | 15-Minute Timeframe | User: 22 trades (+4.86%) | Bot: {len(bot_trades)} trades (+1.66%)</sub>',
        'x': 0.5,
        'xanchor': 'center'
    },
    height=1000,
    xaxis_rangeslider_visible=False,
    hovermode='x unified',
    template='plotly_dark'
)

fig.update_xaxes(title_text="Time", row=3, col=1)
fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)
fig.update_yaxes(title_text="RSI-7", row=2, col=1)
fig.update_yaxes(title_text="Volume", row=3, col=1)

# Save
output_file = data_dir / 'focused_comparison_chart.html'
fig.write_html(str(output_file))

print(f"\n✅ Chart saved to: {output_file}")
print(f"\n📊 Trade Summary:")
print(f"   👤 User: {len(user_entries_long) + len(user_entries_short)} entries (GREEN=long, RED=short, LARGE)")
print(f"   🤖 Bot:  {len(bot_trades)} trades (CYAN=long, ORANGE=short, SMALL)")
print(f"\n💡 Legend:")
print(f"   - LARGE triangles = User trades (your 22 optimal entries)")
print(f"   - SMALL triangles = Bot trades (39 signals)")
print(f"   - SOLID lines = User trade trajectories")
print(f"   - DOTTED lines = Bot trade trajectories")
print(f"\nOpen the HTML file in your browser to explore interactively!")
