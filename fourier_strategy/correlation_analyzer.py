"""
Cross-Indicator Correlation and Phase Analysis

This module analyzes correlations between Fourier-filtered indicators,
detects lead/lag relationships, and calculates spectral coherence.
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.fft import fft
from typing import Dict, List, Tuple
import warnings

warnings.filterwarnings('ignore')


class CorrelationAnalyzer:
    """
    Correlation analyzer for Fourier-filtered indicators.

    Features:
    - Rolling correlation between indicators
    - Phase difference analysis (lead/lag detection)
    - Spectral coherence measurement
    - Correlation matrix generation
    """

    def __init__(self,
                 correlation_window: int = 20,
                 correlation_threshold: float = 0.7):
        """
        Initialize Correlation Analyzer.

        Args:
            correlation_window: Window for rolling correlation (default: 20)
            correlation_threshold: Threshold for significant correlation (default: 0.7)
        """
        self.correlation_window = correlation_window
        self.correlation_threshold = correlation_threshold

    def calculate_rolling_correlation(self,
                                      series1: pd.Series,
                                      series2: pd.Series,
                                      window: int = None) -> pd.Series:
        """
        Calculate rolling correlation between two series.

        Args:
            series1: First series
            series2: Second series
            window: Rolling window (default: use self.correlation_window)

        Returns:
            Rolling correlation series
        """
        if window is None:
            window = self.correlation_window

        corr = series1.rolling(window=window).corr(series2)

        return corr

    def calculate_phase_difference(self,
                                   series1: pd.Series,
                                   series2: pd.Series) -> Tuple[float, int]:
        """
        Calculate phase difference between two signals using FFT.

        Args:
            series1: First series
            series2: Second series

        Returns:
            Tuple of (phase_difference_radians, lag_periods)
                - Positive lag means series1 leads series2
                - Negative lag means series2 leads series1
        """
        # Remove NaN and ensure same length
        df = pd.DataFrame({'s1': series1, 's2': series2}).dropna()

        if len(df) < 10:
            return 0.0, 0

        s1 = df['s1'].values
        s2 = df['s2'].values

        # Apply FFT
        fft1 = fft(s1)
        fft2 = fft(s2)

        # Calculate phase difference
        # Phase = angle of complex number
        phase1 = np.angle(fft1)
        phase2 = np.angle(fft2)

        phase_diff = phase1 - phase2

        # Get dominant frequency's phase difference
        power1 = np.abs(fft1) ** 2
        dominant_idx = np.argmax(power1[1:len(power1)//2]) + 1  # Skip DC component

        dominant_phase_diff = phase_diff[dominant_idx]

        # Convert phase difference to lag in periods
        # Phase difference / (2*pi) * period
        period_estimate = len(s1) / dominant_idx if dominant_idx > 0 else len(s1)
        lag = int(dominant_phase_diff / (2 * np.pi) * period_estimate)

        return dominant_phase_diff, lag

    def calculate_spectral_coherence(self,
                                     series1: pd.Series,
                                     series2: pd.Series,
                                     nperseg: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate spectral coherence between two signals.

        Coherence measures the linear relationship in the frequency domain.
        Values range from 0 (no coherence) to 1 (perfect coherence).

        Args:
            series1: First series
            series2: Second series
            nperseg: Length of each segment for coherence calculation

        Returns:
            Tuple of (frequencies, coherence)
        """
        # Remove NaN
        df = pd.DataFrame({'s1': series1, 's2': series2}).dropna()

        if len(df) < 10:
            return np.array([]), np.array([])

        s1 = df['s1'].values
        s2 = df['s2'].values

        # Default segment length
        if nperseg is None:
            nperseg = min(256, len(s1) // 4)

        # Calculate coherence
        try:
            f, Cxy = signal.coherence(s1, s2, nperseg=nperseg)
            return f, Cxy
        except:
            return np.array([]), np.array([])

    def calculate_correlation_matrix(self,
                                     df: pd.DataFrame,
                                     columns: List[str] = None) -> pd.DataFrame:
        """
        Calculate correlation matrix for selected columns.

        Args:
            df: DataFrame with indicator data
            columns: List of column names to include (default: all filtered columns)

        Returns:
            Correlation matrix DataFrame
        """
        if columns is None:
            # Auto-select filtered columns
            columns = [col for col in df.columns if 'filtered' in col.lower()]

        if len(columns) == 0:
            columns = df.columns.tolist()

        # Calculate correlation matrix
        corr_matrix = df[columns].corr()

        return corr_matrix

    def detect_leading_indicators(self,
                                  price_filtered: pd.Series,
                                  indicators: pd.DataFrame) -> pd.DataFrame:
        """
        Detect which indicators lead or lag price movements.

        Args:
            price_filtered: Filtered price series
            indicators: DataFrame with filtered indicators

        Returns:
            DataFrame with lead/lag analysis
        """
        results = []

        # Get filtered indicator columns
        filtered_cols = [col for col in indicators.columns if 'filtered' in col.lower()]

        for col in filtered_cols:
            # Calculate correlation
            corr = self.calculate_rolling_correlation(
                price_filtered,
                indicators[col]
            ).iloc[-1]  # Get latest correlation

            # Calculate phase difference and lag
            try:
                phase_diff, lag = self.calculate_phase_difference(
                    price_filtered,
                    indicators[col]
                )
            except:
                phase_diff, lag = 0.0, 0

            # Calculate spectral coherence
            try:
                freqs, coherence = self.calculate_spectral_coherence(
                    price_filtered,
                    indicators[col]
                )
                avg_coherence = np.mean(coherence) if len(coherence) > 0 else 0.0
            except:
                avg_coherence = 0.0

            results.append({
                'indicator': col,
                'correlation': corr,
                'phase_difference': phase_diff,
                'lag_periods': lag,
                'lead_lag_type': 'LEADS' if lag > 0 else ('LAGS' if lag < 0 else 'SYNC'),
                'spectral_coherence': avg_coherence,
                'is_significant': abs(corr) >= self.correlation_threshold
            })

        df_results = pd.DataFrame(results)

        # Sort by absolute correlation
        df_results = df_results.sort_values('correlation', key=abs, ascending=False)

        return df_results

    def calculate_rolling_correlation_matrix(self,
                                            df: pd.DataFrame,
                                            columns: List[str],
                                            window: int = None) -> Dict[str, pd.DataFrame]:
        """
        Calculate rolling correlation matrices over time.

        Args:
            df: DataFrame with indicator data
            columns: Columns to include in correlation
            window: Rolling window (default: use self.correlation_window)

        Returns:
            Dictionary with correlation matrices at different time points
        """
        if window is None:
            window = self.correlation_window

        # Calculate rolling correlations for each pair
        rolling_corrs = {}

        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i <= j:  # Only upper triangle (correlation is symmetric)
                    key = f"{col1}_vs_{col2}"
                    rolling_corrs[key] = self.calculate_rolling_correlation(
                        df[col1],
                        df[col2],
                        window
                    )

        # Convert to DataFrame
        corr_df = pd.DataFrame(rolling_corrs)

        return corr_df

    def generate_correlation_heatmap_data(self,
                                         df: pd.DataFrame,
                                         columns: List[str] = None) -> pd.DataFrame:
        """
        Generate data for correlation heatmap visualization.

        Args:
            df: DataFrame with indicators
            columns: Columns to include

        Returns:
            Correlation matrix suitable for heatmap
        """
        if columns is None:
            # Auto-select filtered columns
            columns = [col for col in df.columns if 'filtered' in col.lower()]

        corr_matrix = self.calculate_correlation_matrix(df, columns)

        return corr_matrix

    def analyze_indicator_relationships(self,
                                       price_filtered: pd.Series,
                                       indicators: pd.DataFrame,
                                       ema_data: pd.DataFrame = None) -> Dict:
        """
        Comprehensive analysis of indicator relationships.

        Args:
            price_filtered: Filtered price series
            indicators: DataFrame with all indicators
            ema_data: Optional EMA data

        Returns:
            Dictionary with comprehensive analysis results
        """
        # Get all filtered columns
        filtered_cols = [col for col in indicators.columns if 'filtered' in col.lower()]

        # Add price to the analysis
        analysis_df = indicators[filtered_cols].copy()
        analysis_df['price_filtered'] = price_filtered

        # Include filtered EMAs if provided
        if ema_data is not None:
            ema_filtered_cols = [col for col in ema_data.columns if 'filtered' in col.lower()]
            for col in ema_filtered_cols:
                analysis_df[col] = ema_data[col]

        # 1. Correlation matrix
        corr_matrix = self.calculate_correlation_matrix(analysis_df)

        # 2. Leading indicator analysis
        leading_indicators = self.detect_leading_indicators(price_filtered, indicators)

        # 3. Rolling correlations with price
        rolling_corrs = {}
        for col in filtered_cols:
            rolling_corrs[col] = self.calculate_rolling_correlation(
                price_filtered,
                indicators[col]
            )

        rolling_corr_df = pd.DataFrame(rolling_corrs)

        # 4. Current correlation strengths
        current_corrs = rolling_corr_df.iloc[-1].sort_values(ascending=False)

        # 5. Coherence analysis
        coherence_results = []
        for col in filtered_cols[:5]:  # Top 5 indicators for performance
            try:
                freqs, coh = self.calculate_spectral_coherence(price_filtered, indicators[col])
                if len(coh) > 0:
                    coherence_results.append({
                        'indicator': col,
                        'avg_coherence': np.mean(coh),
                        'max_coherence': np.max(coh)
                    })
            except:
                pass

        coherence_df = pd.DataFrame(coherence_results) if coherence_results else pd.DataFrame()

        return {
            'correlation_matrix': corr_matrix,
            'leading_indicators': leading_indicators,
            'rolling_correlations': rolling_corr_df,
            'current_correlations': current_corrs,
            'spectral_coherence': coherence_df,
            'analysis_timestamp': pd.Timestamp.now()
        }

    def get_correlation_score(self,
                             price_filtered: pd.Series,
                             indicators: pd.DataFrame) -> float:
        """
        Calculate a composite correlation score (0-100).

        Higher score means stronger agreement between price and indicators.

        Args:
            price_filtered: Filtered price series
            indicators: DataFrame with indicators

        Returns:
            Correlation score (0-100)
        """
        # Get filtered columns
        filtered_cols = [col for col in indicators.columns if 'filtered' in col.lower()]

        correlations = []

        for col in filtered_cols:
            corr = self.calculate_rolling_correlation(
                price_filtered,
                indicators[col]
            ).iloc[-1]

            if not np.isnan(corr):
                correlations.append(abs(corr))

        if len(correlations) == 0:
            return 50.0  # Neutral score

        # Average absolute correlation
        avg_corr = np.mean(correlations)

        # Convert to 0-100 scale
        score = avg_corr * 100

        return score
