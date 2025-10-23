#!/usr/bin/env python3
"""
ULTIMATE Comparison Chart with:
- Entry AND exit markers
- Trade direction arrows
- PNL labels on each trade
- Color-coded by profit/loss
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import timedelta

print("\n🎨 Generating ULTIMATE Comparison Chart...")

data_dir = Path(__file__).parent / 'trading_data'
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

# Filter to focused period
start_date = pd.Timestamp('2025-10-05')
end_date = pd.Timestamp('2025-10-22')
df_period = df_15m[(df_15m['timestamp'] >= start_date) & (df_15m['timestamp'] < end_date)].copy()

# Load user's ACTUAL trades
with open(data_dir / 'user_trades_ACTUAL_exits.json', 'r') as f:
    user_data = json.load(f)
user_trades = pd.DataFrame(user_data['trades'])
user_trades['entry_time'] = pd.to_datetime(user_trades['entry_time'])
user_trades['exit_time'] = pd.to_datetime(user_trades['exit_time'])

# Load bot's trades (Iteration 10)
with open(data_dir / 'iteration_10_results.json', 'r') as f:
    bot_data = json.load(f)
bot_trades = pd.DataFrame(bot_data['trades'])
bot_trades['entry_time'] = pd.to_datetime(bot_trades['entry_time'])
bot_trades['exit_time'] = pd.to_datetime(bot_trades['exit_time'])

print(f"📊 Loaded {len(user_trades)} user trades, {len(bot_trades)} bot trades")

# Create chart
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=('Price & Trades (👤=User, 🤖=Bot)', 'RSI-7', 'Volume'),
    row_heights=[0.6, 0.2, 0.2]
)

# Main price chart
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

# USER TRADES with EXITS and PNL
print(f"\n👤 Adding {len(user_trades)} user trades...")
for idx, trade in user_trades.iterrows():
    color = 'green' if trade['profit_pct'] > 0 else 'red'
    opacity = 0.6 if trade['profit_pct'] > 0 else 0.4

    # Entry marker
    entry_symbol = 'triangle-up' if trade['direction'] == 'long' else 'triangle-down'
    fig.add_trace(
        go.Scatter(
            x=[trade['entry_time']],
            y=[trade['entry_price']],
            mode='markers',
            name=f'User #{trade["trade_num"]} Entry',
            marker=dict(
                symbol=entry_symbol,
                size=16,
                color=color,
                line=dict(color='white', width=2)
            ),
            showlegend=False,
            hovertemplate=f"👤 User Trade #{trade['trade_num']}<br>" +
                         f"{trade['direction'].upper()} Entry<br>" +
                         f"${trade['entry_price']:.2f}<extra></extra>"
        ),
        row=1, col=1
    )

    # Exit marker
    exit_symbol = 'x' if trade['profit_pct'] > 0 else 'x'
    fig.add_trace(
        go.Scatter(
            x=[trade['exit_time']],
            y=[trade['exit_price']],
            mode='markers',
            name=f'User #{trade["trade_num"]} Exit',
            marker=dict(
                symbol=exit_symbol,
                size=14,
                color=color,
                line=dict(color='white', width=2)
            ),
            showlegend=False,
            hovertemplate=f"👤 User Trade #{trade['trade_num']}<br>" +
                         f"{trade['direction'].upper()} Exit<br>" +
                         f"${trade['exit_price']:.2f}<br>" +
                         f"PNL: {trade['profit_pct']:+.2f}%<extra></extra>"
        ),
        row=1, col=1
    )

    # Trade line
    fig.add_trace(
        go.Scatter(
            x=[trade['entry_time'], trade['exit_time']],
            y=[trade['entry_price'], trade['exit_price']],
            mode='lines+text',
            line=dict(color=color, width=3, dash='solid'),
            text=['', f"{trade['profit_pct']:+.1f}%"],
            textposition='top center',
            textfont=dict(size=10, color=color),
            showlegend=False,
            hovertemplate=f"👤 User #{trade['trade_num']}<br>" +
                         f"{trade['direction'].upper()}<br>" +
                         f"Entry: ${trade['entry_price']:.2f}<br>" +
                         f"Exit: ${trade['exit_price']:.2f}<br>" +
                         f"PNL: {trade['profit_pct']:+.2f}% (${trade['pnl']:+.2f})<extra></extra>"
        ),
        row=1, col=1
    )

# BOT TRADES with EXITS and PNL
print(f"\n🤖 Adding {len(bot_trades)} bot trades...")
for idx, trade in bot_trades.iterrows():
    color = 'cyan' if trade['profit_pct'] > 0 else 'orange'
    opacity = 0.4 if trade['profit_pct'] > 0 else 0.3

    # Entry marker (smaller)
    entry_symbol = 'triangle-up' if trade['direction'] == 'long' else 'triangle-down'
    fig.add_trace(
        go.Scatter(
            x=[trade['entry_time']],
            y=[trade['entry_price']],
            mode='markers',
            name=f'Bot Entry',
            marker=dict(
                symbol=entry_symbol,
                size=10,
                color=color,
                line=dict(color='white', width=1)
            ),
            showlegend=False,
            hovertemplate=f"🤖 Bot Trade<br>" +
                         f"{trade['direction'].upper()} Entry<br>" +
                         f"${trade['entry_price']:.2f}<extra></extra>"
        ),
        row=1, col=1
    )

    # Exit marker
    fig.add_trace(
        go.Scatter(
            x=[trade['exit_time']],
            y=[trade['exit_price']],
            mode='markers',
            marker=dict(
                symbol='x',
                size=8,
                color=color,
                line=dict(color='white', width=1)
            ),
            showlegend=False,
            hovertemplate=f"🤖 Bot Exit<br>" +
                         f"${trade['exit_price']:.2f}<br>" +
                         f"PNL: {trade['profit_pct']:+.2f}%<extra></extra>"
        ),
        row=1, col=1
    )

    # Trade line (dotted, thinner)
    fig.add_trace(
        go.Scatter(
            x=[trade['entry_time'], trade['exit_time']],
            y=[trade['entry_price'], trade['exit_price']],
            mode='lines',
            line=dict(color=color, width=1, dash='dot'),
            showlegend=False,
            opacity=opacity,
            hovertemplate=f"🤖 Bot Trade<br>" +
                         f"{trade['direction'].upper()}<br>" +
                         f"Entry: ${trade['entry_price']:.2f}<br>" +
                         f"Exit: ${trade['exit_price']:.2f}<br>" +
                         f"PNL: {trade['profit_pct']:+.2f}% (${trade['pnl']:+.2f})<br>" +
                         f"Peak: {trade['peak_profit_pct']:+.2f}%<br>" +
                         f"Reason: {trade['exit_reason']}<extra></extra>"
        ),
        row=1, col=1
    )

# RSI indicator
fig.add_trace(
    go.Scatter(
        x=df_period['timestamp'],
        y=df_period['rsi_7'],
        name='RSI-7',
        line=dict(color='purple', width=1)
    ),
    row=2, col=1
)
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
user_pnl = user_data['total_pnl']
user_return = user_data['return_pct']
bot_pnl = sum(bot_trades['pnl'])
bot_return = (bot_pnl / 1000) * 100

fig.update_layout(
    title={
        'text': '🎯 ULTIMATE Comparison: Bot vs User Trades<br>' +
                f'<sub>👤 User: {len(user_trades)} trades, +{user_return:.2f}% (${user_pnl:+.2f}) | ' +
                f'🤖 Bot: {len(bot_trades)} trades, +{bot_return:.2f}% (${bot_pnl:+.2f})</sub>',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 16}
    },
    height=1100,
    xaxis_rangeslider_visible=False,
    hovermode='closest',
    template='plotly_dark',
    font=dict(size=11)
)

fig.update_xaxes(title_text="Time", row=3, col=1)
fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)
fig.update_yaxes(title_text="RSI-7", row=2, col=1)
fig.update_yaxes(title_text="Volume", row=3, col=1)

# Add legend
fig.add_trace(
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=14, color='green', symbol='triangle-up', line=dict(color='white', width=2)),
        name='👤 User LONG Entry'
    ),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=14, color='red', symbol='triangle-down', line=dict(color='white', width=2)),
        name='👤 User SHORT Entry'
    ),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=14, color='green', symbol='x', line=dict(color='white', width=2)),
        name='👤 User Exit (Profit)'
    ),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=10, color='cyan', symbol='triangle-up', line=dict(color='white', width=1)),
        name='🤖 Bot LONG Entry'
    ),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=10, color='orange', symbol='triangle-down', line=dict(color='white', width=1)),
        name='🤖 Bot SHORT Entry'
    ),
    row=1, col=1
)

# Save
output_file = data_dir / 'ULTIMATE_comparison_chart.html'
fig.write_html(str(output_file))

print(f"\n✅ Chart saved to: {output_file}")
print(f"\n📊 Chart Legend:")
print(f"   👤 USER TRADES:")
print(f"      - Large GREEN/RED triangles = Entry (direction)")
print(f"      - X markers = Exit")
print(f"      - SOLID THICK lines = Trade trajectory")
print(f"      - Green text = Profit % label")
print(f"\n   🤖 BOT TRADES:")
print(f"      - Small CYAN/ORANGE triangles = Entry (direction)")
print(f"      - Small x markers = Exit")
print(f"      - DOTTED THIN lines = Trade trajectory")
print(f"      - Hover for full details (peak, exit reason)")
print(f"\n💡 Hover over any marker or line to see full trade details!")
print(f"\n🎉 Open {output_file} in your browser!\n")
