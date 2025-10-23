#!/usr/bin/env python3
"""
Plot EMA Chart with Colors and Crossovers
Interactive visualization of historical data with all 28 EMAs
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import argparse
from datetime import datetime


class EMAChartPlotter:
    """Plot interactive EMA charts with crossovers"""

    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.df = None

    def load_data(self):
        """Load CSV data"""
        print(f"\n📊 Loading data from {self.csv_file}...")
        self.df = pd.read_csv(self.csv_file)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        print(f"   ✅ Loaded {len(self.df)} rows")
        print(f"   Date range: {self.df['timestamp'].iloc[0]} to {self.df['timestamp'].iloc[-1]}")
        return self.df

    def plot_interactive_chart(self, emas_to_plot='all', window=None):
        """
        Create interactive chart with EMAs and crossovers

        Args:
            emas_to_plot: 'fast' (5,10,20), 'medium' (20,50,100), 'all' (default - all 28 EMAs), or list of periods
            window: Number of recent candles to show (None = all data)
        """
        print(f"\n📈 Creating interactive chart...")

        # Select window - default to ALL data
        if window:
            df_plot = self.df.tail(window).copy()
            print(f"   Showing last {window} candles")
        else:
            df_plot = self.df.copy()
            print(f"   Showing all {len(df_plot)} candles")

        # Determine which EMAs to plot - DEFAULT TO ALL 28 EMAs
        if emas_to_plot == 'fast':
            ema_periods = [5, 10, 20]
        elif emas_to_plot == 'medium':
            ema_periods = [20, 50, 100]
        elif emas_to_plot == 'slow':
            ema_periods = [50, 100, 145]
        elif emas_to_plot == 'all':
            ema_periods = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]
        elif isinstance(emas_to_plot, list):
            ema_periods = emas_to_plot
        else:
            ema_periods = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145]

        print(f"   Plotting {len(ema_periods)} EMAs")

        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=('Price & EMAs', 'Volume', 'Ribbon State')
        )

        # 1. Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df_plot['timestamp'],
                open=df_plot['open'],
                high=df_plot['high'],
                low=df_plot['low'],
                close=df_plot['close'],
                name='Price',
                increasing_line_color='green',
                decreasing_line_color='red'
            ),
            row=1, col=1
        )

        # 2. Plot EMAs with DYNAMIC colors (green when price > EMA, red when price < EMA)
        # EMA40 and EMA100 are always YELLOW

        for ema_period in ema_periods:
            ema_col = f'MMA{ema_period}_value'
            color_col = f'MMA{ema_period}_color'

            if ema_col not in df_plot.columns:
                continue

            # EMA40 and EMA100 are ALWAYS YELLOW (no color changes)
            if ema_period in [40, 100]:
                fig.add_trace(
                    go.Scatter(
                        x=df_plot['timestamp'],
                        y=df_plot[ema_col],
                        name=f'EMA{ema_period}',
                        line=dict(color='#FFD700', width=3),  # Yellow, thicker line
                        opacity=1.0
                    ),
                    row=1, col=1
                )
            else:
                # For all other EMAs: Dynamic color based on price comparison
                # Split the line into segments by color
                if color_col in df_plot.columns:
                    # Find color changes
                    df_plot['color_change'] = (df_plot[color_col] != df_plot[color_col].shift(1))
                    df_plot['segment_id'] = df_plot['color_change'].cumsum()

                    # Plot each color segment separately
                    for segment_id in df_plot['segment_id'].unique():
                        segment = df_plot[df_plot['segment_id'] == segment_id]

                        if len(segment) == 0:
                            continue

                        # Get color for this segment
                        segment_color = segment[color_col].iloc[0]

                        if segment_color == 'green':
                            line_color = '#00FF00'  # Bright green
                        elif segment_color == 'red':
                            line_color = '#FF0000'  # Bright red
                        else:
                            line_color = '#808080'  # Gray for neutral

                        # Determine line width (thicker for key EMAs)
                        line_width = 2 if ema_period in [5, 10, 20, 50] else 1

                        # Only show legend for first segment of each EMA
                        is_first_segment = bool(segment_id == df_plot['segment_id'].iloc[0])

                        fig.add_trace(
                            go.Scatter(
                                x=segment['timestamp'],
                                y=segment[ema_col],
                                name=f'EMA{ema_period}',
                                line=dict(color=line_color, width=line_width),
                                opacity=0.7,
                                showlegend=is_first_segment,  # Only show legend once
                                legendgroup=f'ema{ema_period}',  # Group all segments
                                hovertemplate=f'EMA{ema_period}: %{{y:.2f}}<extra></extra>'
                            ),
                            row=1, col=1
                        )
                else:
                    # Fallback if color column not available
                    fig.add_trace(
                        go.Scatter(
                            x=df_plot['timestamp'],
                            y=df_plot[ema_col],
                            name=f'EMA{ema_period}',
                            line=dict(color='#888888', width=1),
                            opacity=0.5
                        ),
                        row=1, col=1
                    )

        # 3. Mark EMA crossovers
        cross_pairs = [(5, 10), (10, 20), (20, 50), (50, 100)]
        for fast, slow in cross_pairs:
            cross_col = f'ema_cross_{fast}_{slow}'
            if cross_col not in df_plot.columns:
                continue

            # Golden crosses (bullish)
            golden = df_plot[df_plot[cross_col] == 'golden_cross']
            if not golden.empty:
                fig.add_trace(
                    go.Scatter(
                        x=golden['timestamp'],
                        y=golden['close'],
                        mode='markers',
                        name=f'Golden {fast}/{slow}',
                        marker=dict(
                            symbol='triangle-up',
                            size=12,
                            color='lime',
                            line=dict(color='darkgreen', width=2)
                        ),
                        text=[f'EMA{fast} crossed above EMA{slow}'] * len(golden),
                        hovertemplate='%{text}<br>Price: $%{y:.2f}<extra></extra>'
                    ),
                    row=1, col=1
                )

            # Death crosses (bearish)
            death = df_plot[df_plot[cross_col] == 'death_cross']
            if not death.empty:
                fig.add_trace(
                    go.Scatter(
                        x=death['timestamp'],
                        y=death['close'],
                        mode='markers',
                        name=f'Death {fast}/{slow}',
                        marker=dict(
                            symbol='triangle-down',
                            size=12,
                            color='red',
                            line=dict(color='darkred', width=2)
                        ),
                        text=[f'EMA{fast} crossed below EMA{slow}'] * len(death),
                        hovertemplate='%{text}<br>Price: $%{y:.2f}<extra></extra>'
                    ),
                    row=1, col=1
                )

        # 4. Volume bars
        volume_colors = ['green' if df_plot['close'].iloc[i] >= df_plot['open'].iloc[i] else 'red'
                        for i in range(len(df_plot))]

        fig.add_trace(
            go.Bar(
                x=df_plot['timestamp'],
                y=df_plot['volume'],
                name='Volume',
                marker_color=volume_colors,
                opacity=0.5
            ),
            row=2, col=1
        )

        # 5. Ribbon state
        ribbon_colors = {
            'all_green': 'darkgreen',
            'mixed_green': 'lightgreen',
            'mixed': 'gray',
            'mixed_red': 'lightcoral',
            'all_red': 'darkred'
        }

        ribbon_numeric = df_plot['ribbon_state'].map({
            'all_green': 2,
            'mixed_green': 1,
            'mixed': 0,
            'mixed_red': -1,
            'all_red': -2
        })

        fig.add_trace(
            go.Scatter(
                x=df_plot['timestamp'],
                y=ribbon_numeric,
                name='Ribbon State',
                fill='tozeroy',
                line=dict(color='blue', width=1),
                fillcolor='rgba(0, 100, 255, 0.3)'
            ),
            row=3, col=1
        )

        # Update layout
        fig.update_layout(
            title=f'EMA Analysis - {self.csv_file}',
            xaxis_title='Time',
            yaxis_title='Price',
            height=1000,
            hovermode='x unified',
            showlegend=True,
            template='plotly_dark'
        )

        # Update y-axis labels
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="Ribbon", row=3, col=1)

        # Remove rangeslider
        fig.update_xaxes(rangeslider_visible=False)

        return fig

    def save_html(self, fig, output_file='ema_chart.html'):
        """Save chart as HTML"""
        fig.write_html(output_file)
        print(f"\n💾 Chart saved to: {output_file}")
        print(f"   Open in browser to view interactive chart!")

    def show(self, fig):
        """Display chart in browser"""
        fig.show()


def main():
    parser = argparse.ArgumentParser(description='Plot EMA chart with crossovers')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--emas', default='all',
                       help='EMAs to plot: fast, medium, slow, all (default), or comma-separated list (e.g., 5,10,20,50)')
    parser.add_argument('--window', type=int, default=None,
                       help='Number of recent candles to show (default: all data)')
    parser.add_argument('--output', default='ema_chart.html',
                       help='Output HTML file (default: ema_chart.html)')
    parser.add_argument('--no-show', action='store_true',
                       help='Do not open browser (just save HTML)')

    args = parser.parse_args()

    print("="*80)
    print("EMA CHART PLOTTER")
    print("="*80)

    # Parse EMAs
    if args.emas in ['fast', 'medium', 'slow', 'all']:
        emas_to_plot = args.emas
    else:
        emas_to_plot = [int(x.strip()) for x in args.emas.split(',')]

    # Create plotter
    plotter = EMAChartPlotter(args.csv_file)
    plotter.load_data()

    # Create chart
    fig = plotter.plot_interactive_chart(emas_to_plot=emas_to_plot, window=args.window)

    # Save
    plotter.save_html(fig, args.output)

    # Show
    if not args.no_show:
        print("\n🌐 Opening chart in browser...")
        plotter.show(fig)

    print("\n✅ Done!")


if __name__ == '__main__':
    main()
