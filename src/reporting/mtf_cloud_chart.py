#!/usr/bin/env python3
"""
Multi-Timeframe Cloud Chart Generator
Creates interactive Plotly charts with gradient EMA ribbon cloud visualization
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class MTFCloudChartGenerator:
    """
    Generates professional multi-timeframe EMA ribbon cloud charts using Plotly

    Features:
    - Candlestick price chart
    - Gradient cloud overlay (multiple layers for smooth opacity gradient)
    - Cloud strength indicator subplot
    - Interactive hover information
    - Professional styling
    """

    def __init__(
        self,
        output_dir: str = 'charts/mtf_cloud',
        opacity_base: float = 0.35,  # Increased from 0.15 for better visibility
        num_gradient_layers: int = 9,  # One layer per timeframe
        show_individual_layers: bool = True
    ):
        """
        Initialize chart generator

        Args:
            output_dir: Directory to save charts
            opacity_base: Base opacity for gradient layers
            num_gradient_layers: Number of layers for gradient effect (one per timeframe)
            show_individual_layers: Show individual timeframe layers with different opacities
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.opacity_base = opacity_base
        self.num_gradient_layers = num_gradient_layers
        self.show_individual_layers = show_individual_layers

    def create_gradient_cloud_layers(
        self,
        fig: go.Figure,
        df: pd.DataFrame,
        timeframes: List[int],
        ema_periods: List[int],
        row: int = 1
    ):
        """
        Create DYNAMIC gradient cloud layers:
        - Color: Pure green-to-red gradient based on EMA ratio
        - Opacity: Based on compression (tight EMAs = MORE visible, spread EMAs = LESS visible)

        Args:
            fig: Plotly figure object
            df: Aggregated DataFrame with aligned EMAs
            timeframes: List of timeframes in minutes
            ema_periods: List of EMA periods
            row: Subplot row number
        """
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from indicators.gradient_mapper import GradientMapper

        gradient_mapper = GradientMapper()

        # Process timeframes in reverse order (larger first) so smaller TFs overlay on top
        for i, tf_minutes in enumerate(reversed(sorted(timeframes))):
            # Get EMAs for this specific timeframe
            tf_ema_cols = [f'TF{tf_minutes}_MMA{period}' for period in ema_periods
                          if f'TF{tf_minutes}_MMA{period}' in df.columns]

            if not tf_ema_cols:
                continue

            # Calculate min/max boundaries for this timeframe only
            tf_lower = df[tf_ema_cols].min(axis=1)
            tf_upper = df[tf_ema_cols].max(axis=1)

            # Get EMA matrix for this timeframe
            ema_values_matrix = df[tf_ema_cols].values

            # Calculate DYNAMIC properties per candle
            colors_per_candle = []
            compressions = []

            for idx in range(len(df)):
                current_price = df['close'].iloc[idx]
                ema_values = ema_values_matrix[idx]

                # Remove NaN
                ema_values = ema_values[~np.isnan(ema_values)]

                if len(ema_values) == 0:
                    colors_per_candle.append('rgba(127, 127, 0, 0.1)')  # Fallback
                    compressions.append(0.1)
                    continue

                # Calculate ratio of EMAs below price (bullish when high)
                ratio = gradient_mapper.calculate_ema_ratio(current_price, ema_values)

                # Calculate compression (tight = high value, spread = low value)
                compression = gradient_mapper.calculate_compression(ema_values)

                # Get RGB color based on ratio (pure green-red gradient)
                rgb = gradient_mapper.ratio_to_rgb(ratio)

                # DYNAMIC OPACITY based on:
                # 1. Compression (tighter EMAs = more visible)
                # 2. Priority timeframes get boost

                # Base opacity from compression
                # High compression (0.8-1.0) = 0.6-0.9 opacity
                # Low compression (0.0-0.2) = 0.1-0.3 opacity
                opacity = 0.2 + (compression * 0.6)

                # Boost priority timeframes
                if tf_minutes in [3, 5, 8, 13]:
                    opacity = min(opacity * 1.3, 0.95)  # 30% boost, cap at 0.95

                # Create RGBA color string
                color_str = f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})'
                colors_per_candle.append(color_str)
                compressions.append(compression)

            # Since Plotly doesn't support per-point fill colors easily,
            # we'll create segments with similar colors
            # Group consecutive similar colors together

            # For simplicity, use average color/opacity for the whole timeframe
            avg_ratio = np.mean([gradient_mapper.calculate_ema_ratio(
                df['close'].iloc[j],
                ema_values_matrix[j][~np.isnan(ema_values_matrix[j])]
            ) for j in range(len(df)) if len(ema_values_matrix[j][~np.isnan(ema_values_matrix[j])]) > 0])

            avg_compression = np.mean(compressions)
            avg_rgb = gradient_mapper.ratio_to_rgb(avg_ratio)

            # Dynamic opacity based on compression
            avg_opacity = 0.2 + (avg_compression * 0.6)
            if tf_minutes in [3, 5, 8, 13]:
                avg_opacity = min(avg_opacity * 1.3, 0.95)

            fill_color = f'rgba({avg_rgb[0]}, {avg_rgb[1]}, {avg_rgb[2]}, {avg_opacity})'

            # Priority marker
            priority_marker = '⭐' if tf_minutes in [3, 5, 8, 13] else ''

            # Legend name with gradient indicator
            if avg_ratio >= 0.7:
                sentiment_emoji = '🟢'
                sentiment_text = 'Strong Bull'
            elif avg_ratio >= 0.55:
                sentiment_emoji = '🟩'
                sentiment_text = 'Bullish'
            elif avg_ratio >= 0.45:
                sentiment_emoji = '🟨'
                sentiment_text = 'Mixed'
            elif avg_ratio >= 0.3:
                sentiment_emoji = '🟥'
                sentiment_text = 'Bearish'
            else:
                sentiment_emoji = '🔴'
                sentiment_text = 'Strong Bear'

            legend_name = f'{priority_marker}{tf_minutes}min {sentiment_emoji} ({avg_compression*100:.0f}% tight)'

            # Add upper boundary (invisible line)
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=tf_upper,
                    mode='lines',
                    line=dict(color='rgba(0,0,0,0)', width=0),
                    showlegend=False,
                    hoverinfo='skip',
                    name=f'TF{tf_minutes}_upper'
                ),
                row=row,
                col=1
            )

            # Add lower boundary with dynamic fill
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=tf_lower,
                    mode='lines',
                    line=dict(color='rgba(0,0,0,0)', width=0),
                    fill='tonexty',
                    fillcolor=fill_color,
                    showlegend=True,
                    name=legend_name,
                    legendgroup=f'tf{tf_minutes}',
                    hovertemplate=f'<b>{tf_minutes}min Cloud</b><br>' +
                                 f'Sentiment: {sentiment_text}<br>' +
                                 'Upper: %{customdata[0]:.2f}<br>' +
                                 'Lower: %{y:.2f}<br>' +
                                 f'EMAs Below Price: {avg_ratio*100:.0f}%<br>' +
                                 f'Compression: {avg_compression*100:.0f}%<br>' +
                                 '<extra></extra>',
                    customdata=np.column_stack([tf_upper])
                ),
                row=row,
                col=1
            )

    def create_unified_cloud_layer(
        self,
        fig: go.Figure,
        df: pd.DataFrame,
        row: int = 1
    ):
        """
        Create unified cloud layer using aggregated cloud_upper and cloud_lower

        Args:
            fig: Plotly figure object
            df: Aggregated DataFrame with cloud_upper, cloud_lower, cloud_color
            row: Subplot row number
        """
        # Add upper boundary (invisible)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['cloud_upper'],
                mode='lines',
                line=dict(color='rgba(0,0,0,0)', width=0),
                showlegend=False,
                hoverinfo='skip',
                name='cloud_upper_boundary'
            ),
            row=row,
            col=1
        )

        # Add lower boundary with dynamic fill color
        # Since Plotly doesn't support per-point fill colors easily,
        # we'll create segments with different colors

        # Split into segments based on color changes
        df_copy = df.copy()
        df_copy['color_group'] = (df_copy['cloud_color'] != df_copy['cloud_color'].shift()).cumsum()

        for group_id in df_copy['color_group'].unique():
            segment = df_copy[df_copy['color_group'] == group_id]

            if len(segment) == 0:
                continue

            segment_color = segment['cloud_color'].iloc[0]

            # Add segment
            fig.add_trace(
                go.Scatter(
                    x=segment.index,
                    y=segment['cloud_lower'],
                    mode='lines',
                    line=dict(color='rgba(0,0,0,0)', width=0),
                    fill='tonexty',
                    fillcolor=segment_color,
                    showlegend=False,
                    hovertemplate='<b>MTF Cloud</b><br>' +
                                 'Upper: %{customdata[0]:.2f}<br>' +
                                 'Lower: %{y:.2f}<br>' +
                                 'Strength: %{customdata[1]:.0f}/100<br>' +
                                 'Sentiment: %{customdata[2]}<br>' +
                                 '<extra></extra>',
                    customdata=segment[['cloud_upper', 'cloud_strength', 'cloud_sentiment']].values
                ),
                row=row,
                col=1
            )

    def create_chart(
        self,
        aggregated_df: pd.DataFrame,
        timeframes: List[int],
        ema_periods: List[int],
        symbol: str = 'ETH',
        title: str = None,
        show_candlesticks: bool = True,
        show_strength_subplot: bool = True
    ) -> go.Figure:
        """
        Create complete multi-timeframe cloud chart

        Args:
            aggregated_df: Aggregated DataFrame with cloud data
            timeframes: List of timeframes used
            ema_periods: List of EMA periods used
            symbol: Trading symbol
            title: Chart title (auto-generated if None)
            show_candlesticks: Show candlestick overlay
            show_strength_subplot: Show cloud strength indicator subplot

        Returns:
            Plotly figure object
        """
        # Determine subplot layout
        if show_strength_subplot:
            fig = make_subplots(
                rows=2,
                cols=1,
                row_heights=[0.75, 0.25],
                vertical_spacing=0.05,
                subplot_titles=(
                    'Price with Multi-Timeframe EMA Cloud',
                    'Cloud Strength (0=Bearish, 100=Bullish)'
                )
            )
        else:
            fig = make_subplots(
                rows=1,
                cols=1,
                subplot_titles=('Price with Multi-Timeframe EMA Cloud',)
            )

        # Add candlesticks if requested
        if show_candlesticks:
            fig.add_trace(
                go.Candlestick(
                    x=aggregated_df.index,
                    open=aggregated_df['open'],
                    high=aggregated_df['high'],
                    low=aggregated_df['low'],
                    close=aggregated_df['close'],
                    name='Price',
                    increasing_line_color='rgba(0, 255, 0, 0.8)',
                    decreasing_line_color='rgba(255, 0, 0, 0.8)',
                    showlegend=True
                ),
                row=1,
                col=1
            )

        # Add cloud layers
        if self.show_individual_layers:
            # Show individual timeframe layers with gradient opacity
            self.create_gradient_cloud_layers(
                fig=fig,
                df=aggregated_df,
                timeframes=timeframes,
                ema_periods=ema_periods,
                row=1
            )
        else:
            # Show unified cloud with color gradient
            self.create_unified_cloud_layer(
                fig=fig,
                df=aggregated_df,
                row=1
            )

        # Add strength indicator subplot
        if show_strength_subplot:
            # Create color list based on strength values
            strength_colors = []
            for strength in aggregated_df['cloud_strength']:
                if strength >= 70:
                    strength_colors.append('green')
                elif strength >= 55:
                    strength_colors.append('lightgreen')
                elif strength >= 45:
                    strength_colors.append('yellow')
                elif strength >= 30:
                    strength_colors.append('orange')
                else:
                    strength_colors.append('red')

            fig.add_trace(
                go.Bar(
                    x=aggregated_df.index,
                    y=aggregated_df['cloud_strength'],
                    marker=dict(
                        color=aggregated_df['cloud_strength'],
                        colorscale=[
                            [0.0, 'red'],
                            [0.3, 'orange'],
                            [0.45, 'yellow'],
                            [0.55, 'lightgreen'],
                            [1.0, 'green']
                        ],
                        cmin=0,
                        cmax=100,
                        showscale=False
                    ),
                    name='Cloud Strength',
                    showlegend=False,
                    hovertemplate='<b>Cloud Strength</b><br>' +
                                 'Strength: %{y:.0f}/100<br>' +
                                 'Sentiment: %{customdata}<br>' +
                                 '<extra></extra>',
                    customdata=aggregated_df['cloud_sentiment']
                ),
                row=2,
                col=1
            )

            # Add reference lines and labels at 35, 50, 65
            reference_levels = [
                (65, 'green', '🟢 BULLISH ZONE (>65)'),
                (50, 'yellow', '🟡 NEUTRAL (35-65)'),
                (35, 'red', '🔴 BEARISH ZONE (<35)')
            ]

            for level, color, label in reference_levels:
                fig.add_hline(
                    y=level,
                    line_dash='dash',
                    line_color=color,
                    line_width=2,
                    opacity=0.7,
                    row=2,
                    col=1,
                    annotation_text=label,
                    annotation_position='right',
                    annotation_font_size=10,
                    annotation_font_color=color
                )

        # Update layout
        if title is None:
            title = f'{symbol} - Dynamic EMA Cloud | Darker = More Compressed | 🟢 Green = Bullish | 🔴 Red = Bearish | ⭐ = Key TFs (3,5,8,13)'

        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                xanchor='center',
                font=dict(size=14, color='white')
            ),
            xaxis_title='Time',
            yaxis_title='Price (USD)',
            template='plotly_dark',
            height=800 if show_strength_subplot else 600,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation='v',
                yanchor='top',
                y=0.99,
                xanchor='left',
                x=0.01,
                bgcolor='rgba(0,0,0,0.5)'
            )
        )

        # Update x-axis
        fig.update_xaxes(
            rangeslider_visible=False,
            showgrid=True,
            gridcolor='rgba(128,128,128,0.2)'
        )

        # Update y-axis
        fig.update_yaxes(
            showgrid=True,
            gridcolor='rgba(128,128,128,0.2)'
        )

        if show_strength_subplot:
            fig.update_yaxes(
                range=[0, 100],
                title_text='Strength',
                row=2,
                col=1
            )

        return fig

    def save_chart(
        self,
        fig: go.Figure,
        filename: str,
        auto_open: bool = False
    ) -> Path:
        """
        Save chart to HTML file

        Args:
            fig: Plotly figure object
            filename: Output filename (without extension)
            auto_open: Open chart in browser after saving

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / f'{filename}.html'
        fig.write_html(
            str(output_path),
            auto_open=auto_open,
            include_plotlyjs='cdn'
        )

        return output_path

    def create_and_save(
        self,
        aggregated_df: pd.DataFrame,
        timeframes: List[int],
        ema_periods: List[int],
        symbol: str = 'ETH',
        filename: str = None,
        auto_open: bool = False
    ) -> Path:
        """
        Convenience method: create chart and save to file

        Args:
            aggregated_df: Aggregated DataFrame
            timeframes: List of timeframes
            ema_periods: List of EMA periods
            symbol: Trading symbol
            filename: Output filename (auto-generated if None)
            auto_open: Open in browser after saving

        Returns:
            Path to saved file
        """
        print(f"\n{'='*70}")
        print(f"Generating Multi-Timeframe Cloud Chart")
        print(f"{'='*70}")

        # Create chart
        fig = self.create_chart(
            aggregated_df=aggregated_df,
            timeframes=timeframes,
            ema_periods=ema_periods,
            symbol=symbol
        )

        # Auto-generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'mtf_cloud_{symbol}_{timestamp}'

        # Save chart
        output_path = self.save_chart(fig, filename, auto_open)

        print(f"✅ Chart saved: {output_path}")
        print(f"   Timeframes: {timeframes}")
        print(f"   Total EMA lines: {len(timeframes) * len(ema_periods)}")
        print(f"   Candles: {len(aggregated_df)}")
        print(f"{'='*70}\n")

        return output_path
