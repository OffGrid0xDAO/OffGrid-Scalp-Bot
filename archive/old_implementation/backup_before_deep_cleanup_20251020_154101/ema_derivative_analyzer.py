"""
EMA Derivative Analyzer - Track slopes, accelerations, and inflection points
Detects momentum changes and correlates with compression/expansion states
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from collections import deque


class EMADerivativeAnalyzer:
    """
    Analyzes EMA derivatives to detect:
    - Slope (1st derivative): Rate of change
    - Acceleration (2nd derivative): Rate of change of slope
    - Inflection points: Where EMAs change direction
    - Compression/expansion correlation
    """

    def __init__(self, lookback_periods: int = 10):
        """
        Args:
            lookback_periods: Number of periods to use for derivative calculation
        """
        self.lookback_periods = lookback_periods
        self.ema_history = {}  # Store recent EMA values for each period: {ema_period: [(timestamp, value), ...]}
        self.slope_history = {}  # Store recent slope values for each EMA: {ema_period: [(timestamp, slope), ...]}

    def add_ema_value(self, ema_period: int, timestamp: datetime, value: float):
        """
        Add a single EMA value to history for real-time tracking

        Args:
            ema_period: EMA period (e.g., 5, 10, 15)
            timestamp: Timestamp of the value
            value: EMA value
        """
        if ema_period not in self.ema_history:
            self.ema_history[ema_period] = deque(maxlen=self.lookback_periods * 2)
            self.slope_history[ema_period] = deque(maxlen=self.lookback_periods)

        self.ema_history[ema_period].append((timestamp, value))

    def calculate_realtime_derivatives(self, ema_period: int) -> Dict:
        """
        Calculate derivatives for a single EMA in real-time

        Args:
            ema_period: EMA period to analyze

        Returns:
            Dict with slope, acceleration, inflection info, and color
        """
        if ema_period not in self.ema_history or len(self.ema_history[ema_period]) < 2:
            return {
                'slope': 0.0,
                'slope_color': 'gray',
                'acceleration': 0.0,
                'inflection_type': 'none',
                'inflection_strength': 0.0
            }

        # Get recent values
        recent_data = list(self.ema_history[ema_period])
        timestamps = [t for t, v in recent_data]
        values = [v for t, v in recent_data]

        # Calculate slope
        slope = self.calculate_slope(values, timestamps)

        # Determine slope color based on magnitude and direction
        slope_color = self._classify_slope_color(slope)

        # Store slope in history
        if ema_period in self.slope_history:
            self.slope_history[ema_period].append((timestamps[-1], slope))

        # Calculate acceleration
        if ema_period in self.slope_history and len(self.slope_history[ema_period]) >= 2:
            recent_slopes = list(self.slope_history[ema_period])
            slope_timestamps = [t for t, s in recent_slopes]
            slope_values = [s for t, s in recent_slopes]
            accel = self.calculate_acceleration(slope_values, slope_timestamps)
        else:
            accel = 0.0

        # Detect inflection point
        if ema_period in self.slope_history and len(self.slope_history[ema_period]) >= 3:
            recent_slopes = [s for t, s in list(self.slope_history[ema_period])[-5:]]
            inflection = self.detect_inflection_point(recent_slopes)
        else:
            inflection = {'type': 'none', 'strength': 0.0}

        return {
            'slope': slope,
            'slope_color': slope_color,
            'acceleration': accel,
            'inflection_type': inflection['type'],
            'inflection_strength': inflection['strength']
        }

    def _classify_slope_color(self, slope: float) -> str:
        """
        Classify slope into color categories for visualization

        Returns:
            'dark_green' - Strong upward (bullish)
            'light_green' - Weak upward
            'gray' - Flat/neutral
            'light_red' - Weak downward
            'dark_red' - Strong downward (bearish)
        """
        # Thresholds (adjust based on your data scale)
        strong_threshold = 0.001  # 0.1% per second
        weak_threshold = 0.0001   # 0.01% per second

        if slope > strong_threshold:
            return 'dark_green'
        elif slope > weak_threshold:
            return 'light_green'
        elif slope < -strong_threshold:
            return 'dark_red'
        elif slope < -weak_threshold:
            return 'light_red'
        else:
            return 'gray'

    def calculate_slope(self, values: List[float], timestamps: List[datetime]) -> float:
        """
        Calculate slope (1st derivative) using linear regression

        Returns:
            Slope in price units per second
        """
        if len(values) < 2:
            return 0.0

        # Convert timestamps to seconds from first timestamp
        times = [(t - timestamps[0]).total_seconds() for t in timestamps]

        # Linear regression
        n = len(values)
        sum_x = sum(times)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(times, values))
        sum_x2 = sum(x * x for x in times)

        # Slope = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator

        return slope

    def calculate_acceleration(self, slopes: List[float], timestamps: List[datetime]) -> float:
        """
        Calculate acceleration (2nd derivative)

        Returns:
            Acceleration in price units per second²
        """
        if len(slopes) < 2:
            return 0.0

        # Convert timestamps to seconds
        times = [(t - timestamps[0]).total_seconds() for t in timestamps]

        # Linear regression on slopes
        return self.calculate_slope(slopes, timestamps)

    def detect_inflection_point(self, slopes: List[float]) -> Dict:
        """
        Detect if we're at an inflection point (slope changing direction)

        Returns:
            Dict with inflection type and strength
        """
        if len(slopes) < 3:
            return {'type': 'none', 'strength': 0.0}

        recent_slopes = slopes[-3:]

        # Check for direction change
        # Bullish inflection: was falling, now rising
        if recent_slopes[0] < 0 and recent_slopes[1] < 0 and recent_slopes[2] > 0:
            strength = abs(recent_slopes[2] - recent_slopes[0])
            return {'type': 'bullish_inflection', 'strength': strength}

        # Bearish inflection: was rising, now falling
        if recent_slopes[0] > 0 and recent_slopes[1] > 0 and recent_slopes[2] < 0:
            strength = abs(recent_slopes[2] - recent_slopes[0])
            return {'type': 'bearish_inflection', 'strength': strength}

        # Acceleration (slope getting steeper in same direction)
        if all(s > 0 for s in recent_slopes):
            if recent_slopes[2] > recent_slopes[1] > recent_slopes[0]:
                return {'type': 'bullish_acceleration', 'strength': recent_slopes[2] - recent_slopes[0]}

        if all(s < 0 for s in recent_slopes):
            if recent_slopes[2] < recent_slopes[1] < recent_slopes[0]:
                return {'type': 'bearish_acceleration', 'strength': abs(recent_slopes[2] - recent_slopes[0])}

        # Deceleration (slope flattening)
        if all(s > 0 for s in recent_slopes):
            if recent_slopes[2] < recent_slopes[1] < recent_slopes[0]:
                return {'type': 'bullish_deceleration', 'strength': recent_slopes[0] - recent_slopes[2]}

        if all(s < 0 for s in recent_slopes):
            if abs(recent_slopes[2]) < abs(recent_slopes[1]) < abs(recent_slopes[0]):
                return {'type': 'bearish_deceleration', 'strength': abs(recent_slopes[0]) - abs(recent_slopes[2])}

        return {'type': 'none', 'strength': 0.0}

    def analyze_ema_derivatives(self, df: pd.DataFrame, ema_columns: List[str]) -> pd.DataFrame:
        """
        Calculate derivatives for all EMAs in dataframe

        Args:
            df: DataFrame with timestamp and EMA value columns
            ema_columns: List of EMA column names (e.g., ['MMA5_value', 'MMA10_value', ...])

        Returns:
            DataFrame with added derivative columns
        """
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Calculate derivatives for each EMA
        for ema_col in ema_columns:
            if ema_col not in df.columns:
                continue

            ema_num = ema_col.replace('_value', '').replace('MMA', '')

            # Calculate slope (1st derivative)
            slopes = []
            accelerations = []
            inflection_types = []
            inflection_strengths = []

            for i in range(len(df)):
                start_idx = max(0, i - self.lookback_periods + 1)

                # Get recent values and timestamps
                recent_values = df[ema_col].iloc[start_idx:i+1].tolist()
                recent_timestamps = df['timestamp'].iloc[start_idx:i+1].tolist()

                if len(recent_values) >= 2:
                    # Calculate slope
                    slope = self.calculate_slope(recent_values, recent_timestamps)
                    slopes.append(slope)

                    # Calculate acceleration if we have enough slope history
                    if len(slopes) >= 2:
                        recent_slope_timestamps = df['timestamp'].iloc[max(0, i-len(slopes)+1):i+1].tolist()
                        accel = self.calculate_acceleration(slopes[-self.lookback_periods:], recent_slope_timestamps[-self.lookback_periods:])
                        accelerations.append(accel)
                    else:
                        accelerations.append(0.0)

                    # Detect inflection point
                    if len(slopes) >= 3:
                        inflection = self.detect_inflection_point(slopes[-5:])  # Look at last 5 slopes
                        inflection_types.append(inflection['type'])
                        inflection_strengths.append(inflection['strength'])
                    else:
                        inflection_types.append('none')
                        inflection_strengths.append(0.0)
                else:
                    slopes.append(0.0)
                    accelerations.append(0.0)
                    inflection_types.append('none')
                    inflection_strengths.append(0.0)

            # Add derivative columns
            df[f'MMA{ema_num}_slope'] = slopes
            df[f'MMA{ema_num}_accel'] = accelerations
            df[f'MMA{ema_num}_inflection_type'] = inflection_types
            df[f'MMA{ema_num}_inflection_strength'] = inflection_strengths

        return df

    def calculate_compression_state(self, df: pd.DataFrame, ema_columns: List[str]) -> pd.DataFrame:
        """
        Calculate compression/expansion state based on EMA spread

        Returns:
            DataFrame with compression metrics
        """
        df = df.copy()

        compressions = []

        for i in range(len(df)):
            ema_values = []
            for col in ema_columns:
                if col in df.columns:
                    val = df[col].iloc[i]
                    if pd.notna(val) and val != 'N/A':
                        try:
                            ema_values.append(float(val))
                        except:
                            pass

            if len(ema_values) > 0:
                # Calculate compression as coefficient of variation
                # (std / mean) - lower means more compressed
                mean_ema = np.mean(ema_values)
                std_ema = np.std(ema_values)

                if mean_ema > 0:
                    compression = std_ema / mean_ema
                else:
                    compression = 0.0
            else:
                compression = 0.0

            compressions.append(compression)

        df['ema_compression'] = compressions

        # Calculate compression rate of change (expanding vs compressing)
        compression_roc = [0.0]
        for i in range(1, len(compressions)):
            roc = compressions[i] - compressions[i-1]
            compression_roc.append(roc)

        df['compression_roc'] = compression_roc

        # Classify compression state
        compression_states = []
        for comp, roc in zip(compressions, compression_roc):
            if comp < 0.005:  # Very tight
                if roc > 0.0001:
                    state = 'tight_expanding'
                elif roc < -0.0001:
                    state = 'tight_compressing'
                else:
                    state = 'tight_stable'
            elif comp < 0.015:  # Moderate
                if roc > 0.0001:
                    state = 'moderate_expanding'
                elif roc < -0.0001:
                    state = 'moderate_compressing'
                else:
                    state = 'moderate_stable'
            else:  # Wide
                if roc > 0.0001:
                    state = 'wide_expanding'
                elif roc < -0.0001:
                    state = 'wide_compressing'
                else:
                    state = 'wide_stable'

            compression_states.append(state)

        df['compression_state'] = compression_states

        return df

    def correlate_inflections_with_compression(self, df: pd.DataFrame) -> Dict:
        """
        Analyze correlation between inflection points and compression states

        Returns:
            Dict with correlation insights
        """
        if 'compression_state' not in df.columns:
            return {'error': 'compression_state not calculated'}

        # Count inflection points by compression state
        inflection_counts = {}

        for col in df.columns:
            if '_inflection_type' in col:
                for comp_state in df['compression_state'].unique():
                    mask = df['compression_state'] == comp_state
                    inflections = df.loc[mask, col].value_counts().to_dict()

                    for inflection_type, count in inflections.items():
                        if inflection_type != 'none':
                            key = f"{comp_state}_{inflection_type}"
                            inflection_counts[key] = inflection_counts.get(key, 0) + count

        # Find most common patterns
        sorted_patterns = sorted(inflection_counts.items(), key=lambda x: x[1], reverse=True)

        insights = {
            'total_inflections': sum(inflection_counts.values()),
            'top_patterns': [
                {'pattern': pattern, 'count': count}
                for pattern, count in sorted_patterns[:10]
            ],
            'compression_state_distribution': df['compression_state'].value_counts().to_dict()
        }

        return insights

    def find_early_signals(self, df: pd.DataFrame, lead_time_minutes: int = 5) -> Dict:
        """
        Find if inflection points/slope changes predict ribbon flips

        Args:
            df: DataFrame with derivatives and ribbon_state
            lead_time_minutes: How many minutes before ribbon flip to look for signals

        Returns:
            Dict with early signal patterns
        """
        if 'ribbon_state' not in df.columns:
            return {'error': 'ribbon_state not found'}

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Find ribbon flips
        ribbon_flips = []
        for i in range(1, len(df)):
            prev_state = df['ribbon_state'].iloc[i-1]
            curr_state = df['ribbon_state'].iloc[i]

            if prev_state != curr_state:
                ribbon_flips.append({
                    'timestamp': df['timestamp'].iloc[i],
                    'from_state': prev_state,
                    'to_state': curr_state,
                    'index': i
                })

        # For each flip, look back to find early signals
        early_signals = []

        for flip in ribbon_flips:
            flip_time = flip['timestamp']
            lookback_time = flip_time - timedelta(minutes=lead_time_minutes)

            # Get data in the lookback window
            mask = (df['timestamp'] >= lookback_time) & (df['timestamp'] < flip_time)
            lookback_df = df[mask]

            if len(lookback_df) == 0:
                continue

            # Check for inflection points in the lookback period
            inflections_found = []

            for col in lookback_df.columns:
                if '_inflection_type' in col:
                    inflection_types = lookback_df[col].values
                    for inflection in inflection_types:
                        if inflection != 'none':
                            inflections_found.append(inflection)

            if inflections_found:
                early_signals.append({
                    'flip_time': flip_time.isoformat(),
                    'flip_direction': f"{flip['from_state']} -> {flip['to_state']}",
                    'signals_found': inflections_found,
                    'lead_time_seconds': (flip_time - lookback_df['timestamp'].max()).total_seconds()
                })

        # Summarize findings
        summary = {
            'total_ribbon_flips': len(ribbon_flips),
            'flips_with_early_signals': len(early_signals),
            'early_signal_rate': len(early_signals) / len(ribbon_flips) if ribbon_flips else 0,
            'signals': early_signals[:20]  # Show first 20
        }

        return summary

    def generate_report(self, df: pd.DataFrame, output_file: str = 'trading_data/ema_derivative_report.json'):
        """
        Generate comprehensive derivative analysis report
        """
        # Calculate all derivatives
        ema_value_cols = [col for col in df.columns if '_value' in col and col.startswith('MMA')]

        print("📊 Calculating EMA derivatives...")
        df = self.analyze_ema_derivatives(df, ema_value_cols)

        print("📊 Calculating compression states...")
        df = self.calculate_compression_state(df, ema_value_cols)

        print("📊 Correlating inflections with compression...")
        correlation = self.correlate_inflections_with_compression(df)

        print("📊 Finding early warning signals...")
        early_signals = self.find_early_signals(df, lead_time_minutes=5)

        # Generate report
        report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_period': {
                'start': df['timestamp'].min().isoformat(),
                'end': df['timestamp'].max().isoformat(),
                'total_snapshots': len(df)
            },
            'correlation_analysis': correlation,
            'early_signal_analysis': early_signals,
            'recommendations': self._generate_recommendations(correlation, early_signals)
        }

        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"✅ Report saved to {output_file}")

        return df, report

    def _generate_recommendations(self, correlation: Dict, early_signals: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []

        # Check early signal effectiveness
        if early_signals.get('early_signal_rate', 0) > 0.7:
            recommendations.append(
                f"HIGH PRIORITY: {early_signals['early_signal_rate']*100:.0f}% of ribbon flips "
                f"have detectable early signals. Add inflection detection to entry rules!"
            )

        # Check compression patterns
        if 'top_patterns' in correlation:
            top_pattern = correlation['top_patterns'][0] if correlation['top_patterns'] else None
            if top_pattern:
                recommendations.append(
                    f"Most common pattern: {top_pattern['pattern']} ({top_pattern['count']} occurrences). "
                    f"Consider adding this pattern to trading filters."
                )

        # Check for expansion signals
        comp_dist = correlation.get('compression_state_distribution', {})
        expanding_states = sum(v for k, v in comp_dist.items() if 'expanding' in k)
        total_states = sum(comp_dist.values())

        if expanding_states / total_states > 0.3:
            recommendations.append(
                f"Market is expanding {expanding_states/total_states*100:.0f}% of the time. "
                f"This is ideal for momentum trading strategies."
            )

        return recommendations


def main():
    """Test the derivative analyzer on historical data"""
    print("🚀 EMA Derivative Analyzer - Testing on Historical Data")
    print("="*80)

    # Load EMA data
    df = pd.read_csv('trading_data/ema_data_5min.csv')
    print(f"✅ Loaded {len(df)} snapshots from ema_data_5min.csv")

    # Analyze last 4 hours
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    cutoff = datetime.now() - timedelta(hours=4)
    df_recent = df[df['timestamp'] >= cutoff].copy()

    print(f"📊 Analyzing last 4 hours ({len(df_recent)} snapshots)")
    print()

    # Run analysis
    analyzer = EMADerivativeAnalyzer(lookback_periods=5)
    df_analyzed, report = analyzer.generate_report(df_recent)

    # Print summary
    print("\n" + "="*80)
    print("📈 ANALYSIS SUMMARY")
    print("="*80)

    print(f"\nTotal Ribbon Flips: {report['early_signal_analysis']['total_ribbon_flips']}")
    print(f"Flips with Early Signals: {report['early_signal_analysis']['flips_with_early_signals']}")
    print(f"Early Signal Rate: {report['early_signal_analysis']['early_signal_rate']*100:.1f}%")

    print("\n💡 RECOMMENDATIONS:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")

    print("\n" + "="*80)
    print("✅ Analysis complete! Check 'trading_data/ema_derivative_report.json' for full results")

    # Save enhanced data
    df_analyzed.to_csv('trading_data/ema_data_5min_with_derivatives.csv', index=False)
    print("✅ Enhanced data saved to 'trading_data/ema_data_5min_with_derivatives.csv'")


if __name__ == '__main__':
    main()
