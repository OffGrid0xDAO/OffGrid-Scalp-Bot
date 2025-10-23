#!/usr/bin/env python3
"""
Multi-Timeframe EMA RIBBON Chart Generator
Each EMA creates its own gradient ribbon between EMA line and price
Faster EMAs = more opacity, Slower EMAs = less opacity
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class MTFRibbonChart:
    """
    Creates individual EMA ribbons with gradient fill from each EMA to price

    Key differences from cloud chart:
    - Each EMA gets its own ribbon (not one big cloud)
    - Faster EMAs are MORE opaque (more visible)
    - Slower EMAs are LESS opaque (background)
    - Yellow only appears during EMA crossing transitions
    """

    def __init__(self, output_dir: str = 'charts/mtf_ribbon'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def calculate_ema_speed_opacity(self, ema_period: int, next_ema_period: int = None, num_timeframes: int = 4) -> float:
        """
        Calculate opacity for INDIVIDUAL ribbon (between THIS EMA and NEXT EMA)

        Now optimized for fewer timeframes (4 instead of 9) so we can use higher opacity

        Args:
            ema_period: Current EMA period (5 to 200)
            next_ema_period: Next EMA period (for ribbon-to-ribbon distance)
            num_timeframes: Number of timeframes being overlaid

        Returns:
            Moderate opacity (0.05 to 0.25) for good visibility
        """
        # With 4 timeframes × 8 EMAs = 32 ribbon layers
        # We can afford MUCH higher opacity now

        min_period = 5
        max_period = 200

        # Normalize to 0-1 (faster EMAs = higher value)
        normalized = (ema_period - min_period) / (max_period - min_period)

        # Exponential decay - faster EMAs much more visible
        import math
        base_opacity = 0.35 * math.exp(-1.8 * normalized) + 0.08

        # Slight reduction based on number of timeframes
        opacity = base_opacity / (num_timeframes ** 0.3)  # Much gentler reduction

        # Clamp to visible range
        return max(0.05, min(0.25, opacity))  # Much more visible!

    def get_ema_color(
        self,
        current_price: float,
        ema_value: float,
        prev_price: float,
        prev_ema_value: float
    ) -> tuple:
        """
        Determine EMA ribbon color

        Green: Price above EMA (support)
        Red: Price below EMA (resistance)
        Yellow: ONLY during crossing (transition)

        Args:
            current_price: Current price
            ema_value: Current EMA value
            prev_price: Previous candle price
            prev_ema_value: Previous EMA value

        Returns:
            RGB tuple (r, g, b)
        """
        # Check if crossing is happening
        is_crossing = False
        if prev_price and prev_ema_value:
            # Was price above EMA, now below? (or vice versa)
            was_above = prev_price > prev_ema_value
            now_above = current_price > ema_value

            if was_above != now_above:
                is_crossing = True

        if is_crossing:
            # Yellow during transition
            return (255, 255, 0)
        elif current_price > ema_value:
            # Green when price above (EMA is support)
            return (0, 255, 0)
        else:
            # Red when price below (EMA is resistance)
            return (255, 0, 0)

    def create_ribbon_chart(
        self,
        df: pd.DataFrame,
        timeframe: int,
        ema_periods: List[int],
        symbol: str = 'ETH'
    ) -> go.Figure:
        """
        Create ribbon chart for ONE timeframe
        Each EMA gets its own fill to price

        Args:
            df: DataFrame with OHLCV and EMA columns
            timeframe: Timeframe in minutes
            ema_periods: List of EMA periods to plot
            symbol: Trading symbol

        Returns:
            Plotly figure
        """
        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=(f'{symbol} - {timeframe}min EMA Ribbons',)
        )

        # Sort EMAs from slowest to fastest
        # Plot slowest first (background) so faster ones overlay
        sorted_emas = sorted(ema_periods, reverse=True)

        for ema_period in sorted_emas:
            ema_col = f'MMA{ema_period}'

            if ema_col not in df.columns:
                continue

            # Calculate opacity based on EMA speed
            opacity = self.calculate_ema_speed_opacity(ema_period)

            # CRITICAL: We need to create SEGMENTS where color changes dynamically
            # Split the data into segments based on whether price is above/below EMA

            df_copy = df.copy()
            df_copy['is_above'] = df_copy['close'] > df_copy[ema_col]

            # Create segments where color is consistent
            df_copy['color_change'] = (df_copy['is_above'] != df_copy['is_above'].shift()).cumsum()

            for segment_id in df_copy['color_change'].unique():
                segment = df_copy[df_copy['color_change'] == segment_id]

                if len(segment) == 0:
                    continue

                # Determine color for this segment
                is_above = segment['is_above'].iloc[0]

                if is_above:
                    # Price ABOVE EMA = GREEN (EMA is support)
                    fill_color = f'rgba(0, 255, 0, {opacity})'
                    line_color = 'rgba(0, 200, 0, 0.5)'
                else:
                    # Price BELOW EMA = RED (EMA is resistance)
                    fill_color = f'rgba(255, 0, 0, {opacity})'
                    line_color = 'rgba(200, 0, 0, 0.5)'

                # Add price line (invisible, for fill reference)
                fig.add_trace(
                    go.Scatter(
                        x=segment.index,
                        y=segment['close'],
                        mode='lines',
                        line=dict(color='rgba(0,0,0,0)', width=0),
                        showlegend=False,
                        hoverinfo='skip',
                        name=f'price_{ema_period}_{segment_id}'
                    )
                )

                # Add EMA segment with fill to price
                show_legend = bool(segment_id == df_copy['color_change'].iloc[0])  # Only show legend once

                fig.add_trace(
                    go.Scatter(
                        x=segment.index,
                        y=segment[ema_col],
                        mode='lines',
                        line=dict(color=line_color, width=1),
                        fill='tonexty',  # Fill to previous trace (price)
                        fillcolor=fill_color,
                        name=f'EMA{ema_period}',
                        legendgroup=f'ema{ema_period}',
                        showlegend=show_legend,
                        hovertemplate=f'<b>EMA{ema_period}</b><br>' +
                                     'Value: %{y:.2f}<br>' +
                                     f'Opacity: {opacity:.2f}<br>' +
                                     '<extra></extra>'
                    )
                )

        # Add candlesticks on top
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color='rgba(0, 255, 0, 0.8)',
                decreasing_line_color='rgba(255, 0, 0, 0.8)',
                showlegend=True
            )
        )

        # Update layout
        fig.update_layout(
            title=dict(
                text=f'{symbol} {timeframe}min - EMA Ribbons | Darker = Faster EMA | Green = Support | Red = Resistance',
                x=0.5,
                xanchor='center',
                font=dict(size=14, color='white')
            ),
            xaxis_title='Time',
            yaxis_title='Price (USD)',
            template='plotly_dark',
            height=800,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='top',
                y=0.99,
                xanchor='left',
                x=0.01,
                bgcolor='rgba(0,0,0,0.7)'
            )
        )

        fig.update_xaxes(rangeslider_visible=False, showgrid=True, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')

        return fig

    def create_combined_ribbon_chart(
        self,
        mtf_data: Dict[int, pd.DataFrame],
        ema_periods: List[int],
        symbol: str = 'ETH',
        base_timeframe: int = 1,
        downsample_factor: int = 5
    ) -> go.Figure:
        """
        Create ONE chart with ALL timeframes overlaid - OPTIMIZED VERSION
        Uses downsampling and fewer EMAs/timeframes to reduce file size

        Args:
            mtf_data: Dictionary mapping timeframe to DataFrame
            ema_periods: List of EMA periods
            symbol: Trading symbol
            base_timeframe: Base timeframe for x-axis (default 1min)
            downsample_factor: Keep every Nth point (5 = keep 20% of data)

        Returns:
            Combined Plotly figure
        """
        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=(f'{symbol} - Multi-Timeframe Combined EMA Ribbons',)
        )

        # Get the longest timeframe data for price overlay (most complete)
        # Use the first priority timeframe we'll actually plot
        priority_timeframes = [3, 5, 8, 13]  # Skip 1min for performance
        selected_tfs = [tf for tf in priority_timeframes if tf in mtf_data.keys()]

        # Use the selected timeframe with most data for candlesticks
        base_df = mtf_data[selected_tfs[0]] if selected_tfs else mtf_data[base_timeframe]

        # Sort EMAs slowest to fastest (background to foreground)
        sorted_emas = sorted(ema_periods, reverse=True)

        num_timeframes = len(selected_tfs)

        print(f"   Using {num_timeframes} priority timeframes: {selected_tfs}")

        # OPTIMIZATION 2: Reduce EMAs significantly
        optimized_emas = [5, 10, 20, 30, 50, 100, 145, 200]
        selected_emas = [e for e in sorted_emas if e in optimized_emas]

        print(f"   Using {len(selected_emas)} EMAs (from {len(sorted_emas)})")
        print(f"   Downsampling: keeping every {downsample_factor}th point")

        # Process each timeframe
        for tf_minutes in sorted(selected_tfs):
            df = mtf_data[tf_minutes]

            # OPTIMIZATION 3: Downsample the data
            df_sampled = df.iloc[::downsample_factor].copy()

            print(f"   Adding {tf_minutes}min ribbons ({len(df_sampled)} points)...")

            # For each EMA in this timeframe, fill between THIS EMA and NEXT EMA
            for i, ema_period in enumerate(selected_emas):
                ema_col = f'MMA{ema_period}'

                if ema_col not in df_sampled.columns:
                    continue

                # Calculate opacity with num_timeframes adjustment
                opacity = self.calculate_ema_speed_opacity(ema_period, num_timeframes)

                # Determine what to fill to
                if i == len(selected_emas) - 1:
                    # Fastest EMA - fill to price
                    fill_to_series = df_sampled['close']
                else:
                    # Fill to next faster EMA
                    next_ema_period = selected_emas[i + 1]
                    next_ema_col = f'MMA{next_ema_period}'
                    if next_ema_col in df_sampled.columns:
                        fill_to_series = df_sampled[next_ema_col]
                    else:
                        continue

                # Dynamic color based on price vs EMA
                df_sampled['is_above'] = df_sampled['close'] > df_sampled[ema_col]
                df_sampled['color_change'] = (df_sampled['is_above'] != df_sampled['is_above'].shift()).cumsum()

                # Only create segments for significant changes (merge small segments)
                for segment_id in df_sampled['color_change'].unique():
                    segment = df_sampled[df_sampled['color_change'] == segment_id]

                    # Skip very small segments (< 3 points)
                    if len(segment) < 3:
                        continue

                    is_above = segment['is_above'].iloc[0]

                    if is_above:
                        fill_color = f'rgba(0, 255, 0, {opacity})'
                        line_color = 'rgba(0, 200, 0, 0.1)'
                    else:
                        fill_color = f'rgba(255, 0, 0, {opacity})'
                        line_color = 'rgba(200, 0, 0, 0.1)'

                    # Add reference line (next EMA or price) - invisible
                    fig.add_trace(
                        go.Scatter(
                            x=segment.index,
                            y=fill_to_series.loc[segment.index],
                            mode='lines',
                            line=dict(color='rgba(0,0,0,0)', width=0),
                            showlegend=False,
                            hoverinfo='skip',
                            name=f'ref_{tf_minutes}_{ema_period}_{segment_id}'
                        )
                    )

                    # Add THIS EMA line with fill to reference
                    show_legend = bool(tf_minutes == selected_tfs[0] and
                                      i == 0 and segment_id == df_sampled['color_change'].iloc[0])

                    fig.add_trace(
                        go.Scatter(
                            x=segment.index,
                            y=segment[ema_col],
                            mode='lines',
                            line=dict(color=line_color, width=0.2),
                            fill='tonexty',
                            fillcolor=fill_color,
                            name=f'TF{tf_minutes}min',
                            legendgroup=f'tf{tf_minutes}',
                            showlegend=show_legend,
                            hovertemplate=f'<b>TF{tf_minutes}min EMA{ema_period}</b><br>' +
                                         'Value: %{y:.2f}<br>' +
                                         f'Opacity: {opacity:.3f}<br>' +
                                         '<extra></extra>'
                        )
                    )

        # Add candlesticks from base timeframe on top
        fig.add_trace(
            go.Candlestick(
                x=base_df.index,
                open=base_df['open'],
                high=base_df['high'],
                low=base_df['low'],
                close=base_df['close'],
                name='Price',
                increasing_line_color='rgba(255, 255, 255, 0.8)',
                decreasing_line_color='rgba(128, 128, 128, 0.8)',
                showlegend=True
            )
        )

        # Update layout
        fig.update_layout(
            title=dict(
                text=f'{symbol} - ALL TIMEFRAMES COMBINED | Yellow = Overlap | Darker = Faster EMAs',
                x=0.5,
                xanchor='center',
                font=dict(size=14, color='white')
            ),
            xaxis_title='Time',
            yaxis_title='Price (USD)',
            template='plotly_dark',
            height=900,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='top',
                y=0.99,
                xanchor='right',
                x=0.99,
                bgcolor='rgba(0,0,0,0.7)'
            )
        )

        fig.update_xaxes(rangeslider_visible=False, showgrid=True, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')

        return fig

    def create_multi_timeframe_ribbons(
        self,
        mtf_data: Dict[int, pd.DataFrame],
        ema_periods: List[int],
        symbol: str = 'ETH',
        timeframes_to_plot: List[int] = None
    ) -> Dict[int, go.Figure]:
        """
        Create ribbon charts for multiple timeframes

        Args:
            mtf_data: Dictionary mapping timeframe to DataFrame
            ema_periods: List of EMA periods
            symbol: Trading symbol
            timeframes_to_plot: Specific timeframes to plot (default: all)

        Returns:
            Dictionary mapping timeframe to figure
        """
        if timeframes_to_plot is None:
            timeframes_to_plot = sorted(mtf_data.keys())

        figures = {}

        for tf in timeframes_to_plot:
            if tf not in mtf_data:
                print(f"⚠️  Skipping {tf}min - no data")
                continue

            print(f"📊 Creating ribbon chart for {tf}min...")
            fig = self.create_ribbon_chart(
                df=mtf_data[tf],
                timeframe=tf,
                ema_periods=ema_periods,
                symbol=symbol
            )
            figures[tf] = fig

        return figures

    def save_charts(
        self,
        figures: Dict[int, go.Figure],
        symbol: str = 'ETH',
        auto_open: bool = False
    ) -> List[Path]:
        """
        Save all charts to HTML files

        Args:
            figures: Dictionary of timeframe to figure
            symbol: Trading symbol
            auto_open: Open charts in browser

        Returns:
            List of saved file paths
        """
        saved_paths = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        for tf, fig in figures.items():
            filename = f'ribbon_{symbol}_{tf}min_{timestamp}.html'
            output_path = self.output_dir / filename

            fig.write_html(
                str(output_path),
                auto_open=auto_open,
                include_plotlyjs='cdn'
            )

            saved_paths.append(output_path)
            print(f"✅ Saved: {output_path}")

        return saved_paths
