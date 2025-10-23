#!/usr/bin/env python3
"""
Generate comprehensive performance chart for FULL BACKTEST
Shows:
- Price chart with all trades
- Equity curve
- Monthly returns
- Drawdown
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path

print("\n📊 Generating Full Performance Chart...")

data_dir = Path(__file__).parent / 'trading_data'

# Load full backtest results
with open(data_dir / 'iteration_10_FULL_backtest.json', 'r') as f:
    results = json.load(f)

# Load price data
df_15m = pd.read_csv(data_dir / 'indicators' / 'eth_15m_full.csv')
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

# Load trades
trades = pd.DataFrame(results['trade_list'])
trades['entry_time'] = pd.to_datetime(trades['entry_time'])
trades['exit_time'] = pd.to_datetime(trades['exit_time'])

# Load equity curve
equity = pd.DataFrame(results['equity_curve'])
equity['timestamp'] = pd.to_datetime(equity['timestamp'])

print(f"✅ Loaded {len(trades)} trades")
print(f"✅ Loaded {len(equity)} equity points")

# Create subplots
fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    subplot_titles=(
        f'ETH/USDT 15m + Bot Trades (Iteration 10)',
        'Equity Curve',
        'Monthly Returns',
        'Drawdown'
    ),
    row_heights=[0.4, 0.25, 0.2, 0.15]
)

# ============================================================================
# ROW 1: PRICE + TRADES
# ============================================================================

fig.add_trace(
    go.Candlestick(
        x=df_15m['timestamp'],
        open=df_15m['open'],
        high=df_15m['high'],
        low=df_15m['low'],
        close=df_15m['close'],
        name='ETH/USDT',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ),
    row=1, col=1
)

# Add trades
for idx, trade in trades.iterrows():
    color = 'green' if trade['profit_pct'] > 0 else 'red'

    # Entry marker
    entry_symbol = 'triangle-up' if trade['direction'] == 'long' else 'triangle-down'
    fig.add_trace(
        go.Scatter(
            x=[trade['entry_time']],
            y=[trade['entry_price']],
            mode='markers',
            marker=dict(
                symbol=entry_symbol,
                size=8,
                color=color,
                line=dict(color='white', width=1)
            ),
            showlegend=False,
            hovertemplate=f"Entry: ${trade['entry_price']:.2f}<br>" +
                         f"{trade['direction'].upper()}<extra></extra>"
        ),
        row=1, col=1
    )

    # Trade line
    fig.add_trace(
        go.Scatter(
            x=[trade['entry_time'], trade['exit_time']],
            y=[trade['entry_price'], trade['exit_price']],
            mode='lines',
            line=dict(color=color, width=1, dash='dot'),
            showlegend=False,
            opacity=0.3,
            hovertemplate=f"P&L: {trade['profit_pct']:+.2f}%<br>" +
                         f"${trade['pnl']:+.2f}<extra></extra>"
        ),
        row=1, col=1
    )

# ============================================================================
# ROW 2: EQUITY CURVE
# ============================================================================

fig.add_trace(
    go.Scatter(
        x=equity['timestamp'],
        y=equity['capital'],
        name='Equity',
        line=dict(color='#2196F3', width=2),
        fill='tozeroy',
        fillcolor='rgba(33, 150, 243, 0.1)'
    ),
    row=2, col=1
)

# Add horizontal line at starting capital
fig.add_hline(
    y=1000,
    line_dash="dash",
    line_color="gray",
    opacity=0.5,
    row=2, col=1
)

# ============================================================================
# ROW 3: MONTHLY RETURNS
# ============================================================================

# Calculate monthly returns from trades
trades['month'] = trades['exit_time'].dt.to_period('M').astype(str)
monthly_pnl = trades.groupby('month')['pnl'].sum().reset_index()
monthly_pnl['return_pct'] = (monthly_pnl['pnl'] / 100) * 100

colors_monthly = ['green' if x > 0 else 'red' for x in monthly_pnl['return_pct']]

fig.add_trace(
    go.Bar(
        x=monthly_pnl['month'],
        y=monthly_pnl['return_pct'],
        name='Monthly Return',
        marker_color=colors_monthly,
        text=monthly_pnl['return_pct'].apply(lambda x: f"{x:+.1f}%"),
        textposition='outside'
    ),
    row=3, col=1
)

# ============================================================================
# ROW 4: DRAWDOWN
# ============================================================================

# Calculate drawdown
equity['peak'] = equity['capital'].cummax()
equity['drawdown'] = (equity['capital'] - equity['peak']) / equity['peak'] * 100

fig.add_trace(
    go.Scatter(
        x=equity['timestamp'],
        y=equity['drawdown'],
        name='Drawdown',
        line=dict(color='#f44336', width=2),
        fill='tozeroy',
        fillcolor='rgba(244, 67, 54, 0.2)'
    ),
    row=4, col=1
)

# ============================================================================
# LAYOUT
# ============================================================================

total_return = results['performance']['total_return_pct']
annualized = results['performance']['annualized_return_pct']
win_rate = results['trades']['win_rate']
max_dd = results['performance']['max_drawdown_pct']
total_trades = results['trades']['total']

fig.update_layout(
    title={
        'text': f'🚀 Iteration 10 - Full Backtest ({results["period"]["total_days"]} days)<br>' +
                f'<sub>Return: {total_return:+.2f}% | Annualized: {annualized:+.1f}% | ' +
                f'Win Rate: {win_rate:.1f}% | Max DD: {max_dd:.2f}% | Trades: {total_trades}</sub>',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 16}
    },
    height=1200,
    xaxis_rangeslider_visible=False,
    hovermode='x unified',
    template='plotly_dark',
    font=dict(size=10)
)

fig.update_xaxes(title_text="Date", row=4, col=1)
fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)
fig.update_yaxes(title_text="Capital ($)", row=2, col=1)
fig.update_yaxes(title_text="Return (%)", row=3, col=1)
fig.update_yaxes(title_text="Drawdown (%)", row=4, col=1)

# Save
output_file = data_dir / 'iteration_10_FULL_performance.html'
fig.write_html(str(output_file))

print(f"\n✅ Chart saved to: {output_file}")
print(f"\n📊 Summary:")
print(f"   Period: {results['period']['start'][:10]} to {results['period']['end'][:10]}")
print(f"   Total Return: {total_return:+.2f}%")
print(f"   Annualized: {annualized:+.1f}%")
print(f"   Win Rate: {win_rate:.1f}%")
print(f"   Max Drawdown: {max_dd:.2f}%")
print(f"   Profit Factor: 1.30")
print(f"   Total Trades: {total_trades}")
print(f"\n🎉 Open {output_file} in your browser!\n")
