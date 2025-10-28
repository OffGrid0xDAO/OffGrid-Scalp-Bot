#!/usr/bin/env python3
"""
Multi-Timeframe Analyzer for Fourier + Fibonacci Strategy

Analyzes price across multiple timeframes (1m, 3m, 5m, 10m, 15m, 30m, 1h)
and detects confluence when signals align across timeframes.

This creates MAXIMUM PROBABILITY setups when:
- Short-term + medium-term + long-term all agree
- Fourier signals aligned across timeframes
- Fibonacci ribbons compressed on multiple timeframes
- Cross-timeframe fractal confirmation

Think of it as a "zoom out/zoom in" system where we only trade
when ALL timeframes are pointing the same direction.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.fibonacci_ribbon_analyzer import FibonacciRibbonAnalyzer
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter


class MultiTimeframeAnalyzer:
    """
    Analyzes Fourier + Fibonacci signals across multiple timeframes

    Timeframe hierarchy:
    - Short-term: 1m, 3m, 5m (scalping/intraday)
    - Medium-term: 10m, 15m, 30m (day trading)
    - Long-term: 1h+ (swing trading/trend)
    """

    # Supported timeframes
    TIMEFRAMES = ['1m', '3m', '5m', '10m', '15m', '30m', '1h']

    # Timeframe categories
    SHORT_TERM = ['1m', '3m', '5m']
    MEDIUM_TERM = ['10m', '15m', '30m']
    LONG_TERM = ['1h']

    def __init__(self,
                 symbol: str = 'ETH',
                 timeframes: List[str] = None,
                 n_harmonics: int = 5,
                 noise_threshold: float = 0.3):
        """
        Initialize multi-timeframe analyzer

        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to analyze (default: all)
            n_harmonics: Fourier harmonics
            noise_threshold: Noise filtering threshold
        """
        self.symbol = symbol
        self.timeframes = timeframes if timeframes else self.TIMEFRAMES
        self.n_harmonics = n_harmonics
        self.noise_threshold = noise_threshold

        # Storage for data and analysis
        self.data = {}  # {timeframe: DataFrame}
        self.fourier_results = {}  # {timeframe: results}
        self.fibonacci_results = {}  # {timeframe: results}

        # Data adapter
        self.adapter = HyperliquidDataAdapter(symbol=symbol)

    def fetch_all_timeframes(self, days_back: int = 30) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for all timeframes

        Args:
            days_back: Days of historical data

        Returns:
            dict: {timeframe: DataFrame}
        """
        print("\n" + "="*80)
        print(f"📊 FETCHING MULTI-TIMEFRAME DATA FOR {self.symbol}")
        print("="*80)

        for tf in self.timeframes:
            print(f"\n   Fetching {tf} data...")
            try:
                df = self.adapter.fetch_ohlcv(
                    interval=tf,
                    days_back=days_back,
                    use_checkpoint=False
                )
                self.data[tf] = df
                print(f"   ✅ {tf}: {len(df)} candles ({df.index[0]} to {df.index[-1]})")
            except Exception as e:
                print(f"   ❌ {tf}: Failed to fetch - {e}")

        print(f"\n✅ Fetched {len(self.data)}/{len(self.timeframes)} timeframes")
        return self.data

    def analyze_timeframe(self,
                         timeframe: str,
                         run_backtest: bool = False) -> Dict:
        """
        Run Fourier + Fibonacci analysis on a single timeframe

        Args:
            timeframe: Timeframe to analyze
            run_backtest: Whether to run backtest

        Returns:
            dict with analysis results
        """
        if timeframe not in self.data:
            raise ValueError(f"No data for timeframe {timeframe}")

        df = self.data[timeframe]

        print(f"\n🔬 Analyzing {timeframe}...")

        # 1. Fourier strategy analysis
        fourier_strategy = FourierTradingStrategy(
            n_harmonics=self.n_harmonics,
            noise_threshold=self.noise_threshold,
            base_ema_period=28,
            correlation_threshold=0.6,
            min_signal_strength=0.3,
            max_holding_periods=168,
            initial_capital=10000.0,
            commission=0.001
        )

        fourier_results = fourier_strategy.run(df, run_backtest=run_backtest, verbose=False)

        # 2. Fibonacci ribbon analysis
        fib_analyzer = FibonacciRibbonAnalyzer(
            n_harmonics=self.n_harmonics,
            noise_threshold=self.noise_threshold
        )

        fib_results = fib_analyzer.analyze(df)

        # Store results
        self.fourier_results[timeframe] = fourier_results
        self.fibonacci_results[timeframe] = fib_results

        # Get current signals (last candle)
        last_idx = -1

        fourier_signal = fourier_results['output_df']['composite_signal'].iloc[last_idx]
        fib_confluence = fib_results['signals']['fibonacci_confluence'].iloc[last_idx]
        fib_alignment = fib_results['signals']['fibonacci_alignment'].iloc[last_idx]
        fib_compression = fib_results['signals']['fibonacci_compression'].iloc[last_idx]

        print(f"   ✅ {timeframe} signals:")
        print(f"      Fourier: {fourier_signal:.3f}")
        print(f"      Fib Confluence: {fib_confluence:.1f}")
        print(f"      Fib Alignment: {fib_alignment:.1f}")

        return {
            'timeframe': timeframe,
            'fourier_results': fourier_results,
            'fibonacci_results': fib_results,
            'current_signals': {
                'fourier_signal': fourier_signal,
                'fib_confluence': fib_confluence,
                'fib_alignment': fib_alignment,
                'fib_compression': fib_compression
            }
        }

    def analyze_all_timeframes(self, run_backtest: bool = False) -> Dict:
        """
        Analyze all timeframes

        Args:
            run_backtest: Whether to run backtests

        Returns:
            dict with all analyses
        """
        print("\n" + "="*80)
        print("🔬 MULTI-TIMEFRAME ANALYSIS")
        print("="*80)

        analyses = {}

        for tf in self.timeframes:
            if tf in self.data:
                try:
                    analyses[tf] = self.analyze_timeframe(tf, run_backtest=run_backtest)
                except Exception as e:
                    print(f"   ❌ {tf}: Analysis failed - {e}")

        print(f"\n✅ Analyzed {len(analyses)}/{len(self.timeframes)} timeframes")

        return analyses

    def calculate_timeframe_confluence(self, analyses: Dict = None) -> Dict:
        """
        Calculate confluence score across all timeframes

        When all timeframes agree → High confidence signal!

        Args:
            analyses: Analysis results (if None, use stored)

        Returns:
            dict with confluence scores
        """
        if analyses is None:
            analyses = {
                tf: {
                    'current_signals': {
                        'fourier_signal': self.fourier_results[tf]['output_df']['composite_signal'].iloc[-1],
                        'fib_confluence': self.fibonacci_results[tf]['signals']['fibonacci_confluence'].iloc[-1],
                        'fib_alignment': self.fibonacci_results[tf]['signals']['fibonacci_alignment'].iloc[-1],
                        'fib_compression': self.fibonacci_results[tf]['signals']['fibonacci_compression'].iloc[-1]
                    }
                }
                for tf in self.timeframes if tf in self.fourier_results
            }

        print("\n" + "="*80)
        print("🎯 CALCULATING CROSS-TIMEFRAME CONFLUENCE")
        print("="*80)

        # Collect signals from all timeframes
        fourier_signals = []
        fib_confluences = []
        fib_alignments = []
        fib_compressions = []

        for tf, analysis in analyses.items():
            signals = analysis['current_signals']
            fourier_signals.append(signals['fourier_signal'])
            fib_confluences.append(signals['fib_confluence'])
            fib_alignments.append(signals['fib_alignment'])
            fib_compressions.append(signals['fib_compression'])

        # Calculate agreement scores

        # 1. Fourier direction agreement
        bullish_fourier = sum(1 for s in fourier_signals if s > 0.3)
        bearish_fourier = sum(1 for s in fourier_signals if s < -0.3)
        total_tf = len(fourier_signals)

        fourier_agreement = max(bullish_fourier, bearish_fourier) / total_tf * 100
        fourier_direction = 'BULLISH' if bullish_fourier > bearish_fourier else 'BEARISH'

        # 2. Fibonacci alignment agreement
        bullish_fib = sum(1 for a in fib_alignments if a > 60)
        bearish_fib = sum(1 for a in fib_alignments if a < -60)

        fib_agreement = max(bullish_fib, bearish_fib) / total_tf * 100
        fib_direction = 'BULLISH' if bullish_fib > bearish_fib else 'BEARISH'

        # 3. Confluence level (average across timeframes)
        avg_confluence = np.mean(fib_confluences)

        # 4. Compression level (average)
        avg_compression = np.mean(fib_compressions)

        # 5. Overall multi-timeframe confluence score
        mtf_score = (
            fourier_agreement * 0.3 +      # 30% weight
            fib_agreement * 0.3 +          # 30% weight
            avg_confluence * 0.25 +        # 25% weight
            avg_compression * 0.15         # 15% weight
        )

        # 6. Direction consensus
        overall_direction = fourier_direction if fourier_direction == fib_direction else 'NEUTRAL'

        confluence_data = {
            'mtf_score': mtf_score,
            'fourier_agreement': fourier_agreement,
            'fourier_direction': fourier_direction,
            'fib_agreement': fib_agreement,
            'fib_direction': fib_direction,
            'overall_direction': overall_direction,
            'avg_confluence': avg_confluence,
            'avg_compression': avg_compression,
            'timeframes_analyzed': total_tf
        }

        print(f"\n📊 Multi-Timeframe Confluence:")
        print(f"   Overall Score: {mtf_score:.1f}/100")
        print(f"   Direction: {overall_direction}")
        print(f"   Fourier Agreement: {fourier_agreement:.1f}% ({fourier_direction})")
        print(f"   Fibonacci Agreement: {fib_agreement:.1f}% ({fib_direction})")
        print(f"   Avg Confluence: {avg_confluence:.1f}")
        print(f"   Avg Compression: {avg_compression:.1f}")
        print(f"   Timeframes: {total_tf}")

        return confluence_data

    def generate_mtf_signals(self,
                            confluence_threshold: float = 75,
                            agreement_threshold: float = 70) -> Dict:
        """
        Generate trading signals based on multi-timeframe confluence

        Args:
            confluence_threshold: Minimum MTF score for signal
            agreement_threshold: Minimum directional agreement

        Returns:
            dict with signal recommendation
        """
        # Get latest confluence
        confluence = self.calculate_timeframe_confluence()

        mtf_score = confluence['mtf_score']
        direction = confluence['overall_direction']
        fourier_agreement = confluence['fourier_agreement']
        fib_agreement = confluence['fib_agreement']

        # Signal generation logic
        signal = 0  # 0 = no signal, 1 = long, -1 = short
        confidence = 0
        reason = "No clear signal"

        # LONG signal conditions
        if (
            direction == 'BULLISH' and
            mtf_score >= confluence_threshold and
            fourier_agreement >= agreement_threshold and
            fib_agreement >= agreement_threshold
        ):
            signal = 1
            confidence = mtf_score
            reason = f"Multi-timeframe LONG: {fourier_agreement:.0f}% Fourier + {fib_agreement:.0f}% Fib agreement"

        # SHORT signal conditions
        elif (
            direction == 'BEARISH' and
            mtf_score >= confluence_threshold and
            fourier_agreement >= agreement_threshold and
            fib_agreement >= agreement_threshold
        ):
            signal = -1
            confidence = mtf_score
            reason = f"Multi-timeframe SHORT: {fourier_agreement:.0f}% Fourier + {fib_agreement:.0f}% Fib agreement"

        else:
            confidence = mtf_score
            reason = f"Insufficient confluence (score: {mtf_score:.1f}, need {confluence_threshold})"

        signal_data = {
            'signal': signal,
            'direction': 'LONG' if signal == 1 else ('SHORT' if signal == -1 else 'NEUTRAL'),
            'confidence': confidence,
            'reason': reason,
            'confluence': confluence
        }

        print("\n" + "="*80)
        print("🎯 MULTI-TIMEFRAME SIGNAL")
        print("="*80)
        print(f"   Signal: {signal_data['direction']}")
        print(f"   Confidence: {confidence:.1f}/100")
        print(f"   Reason: {reason}")

        return signal_data

    def get_timeframe_breakdown(self) -> pd.DataFrame:
        """
        Get breakdown of signals by timeframe

        Returns:
            DataFrame with signal breakdown
        """
        breakdown = []

        for tf in self.timeframes:
            if tf in self.fourier_results:
                fourier_signal = self.fourier_results[tf]['output_df']['composite_signal'].iloc[-1]
                fib_confluence = self.fibonacci_results[tf]['signals']['fibonacci_confluence'].iloc[-1]
                fib_alignment = self.fibonacci_results[tf]['signals']['fibonacci_alignment'].iloc[-1]

                breakdown.append({
                    'Timeframe': tf,
                    'Fourier Signal': f"{fourier_signal:.3f}",
                    'Direction': 'LONG' if fourier_signal > 0.3 else ('SHORT' if fourier_signal < -0.3 else 'NEUTRAL'),
                    'Fib Confluence': f"{fib_confluence:.1f}",
                    'Fib Alignment': f"{fib_alignment:.1f}",
                    'Agreement': '✅' if abs(fourier_signal) > 0.3 else '❌'
                })

        return pd.DataFrame(breakdown)

    def analyze_complete(self,
                        days_back: int = 30,
                        confluence_threshold: float = 75,
                        agreement_threshold: float = 70) -> Dict:
        """
        Complete multi-timeframe analysis pipeline

        Args:
            days_back: Days of data to fetch
            confluence_threshold: Min confluence for signal
            agreement_threshold: Min agreement for signal

        Returns:
            dict with complete analysis
        """
        print("\n" + "╔" + "═"*78 + "╗")
        print("║" + " "*18 + "MULTI-TIMEFRAME ANALYSIS PIPELINE" + " "*27 + "║")
        print("╚" + "═"*78 + "╝")

        # Step 1: Fetch all timeframes
        self.fetch_all_timeframes(days_back=days_back)

        # Step 2: Analyze each timeframe
        analyses = self.analyze_all_timeframes(run_backtest=False)

        # Step 3: Calculate confluence
        confluence = self.calculate_timeframe_confluence(analyses)

        # Step 4: Generate signals
        signal = self.generate_mtf_signals(
            confluence_threshold=confluence_threshold,
            agreement_threshold=agreement_threshold
        )

        # Step 5: Get breakdown
        breakdown = self.get_timeframe_breakdown()

        print("\n" + "="*80)
        print("TIMEFRAME BREAKDOWN")
        print("="*80)
        print(breakdown.to_string(index=False))

        return {
            'data': self.data,
            'analyses': analyses,
            'confluence': confluence,
            'signal': signal,
            'breakdown': breakdown
        }


if __name__ == '__main__':
    """Test multi-timeframe analyzer"""
    print("\n" + "╔" + "═"*78 + "╗")
    print("║" + " "*20 + "MULTI-TIMEFRAME ANALYZER TEST" + " "*29 + "║")
    print("╚" + "═"*78 + "╝\n")

    # Initialize analyzer
    analyzer = MultiTimeframeAnalyzer(
        symbol='ETH',
        timeframes=['5m', '15m', '30m', '1h'],  # Start with 4 timeframes
        n_harmonics=5,
        noise_threshold=0.3
    )

    # Run complete analysis
    results = analyzer.analyze_complete(
        days_back=7,  # 7 days for faster testing
        confluence_threshold=70,
        agreement_threshold=65
    )

    print("\n✅ Multi-timeframe analysis complete!")
    print(f"\n🎯 FINAL SIGNAL: {results['signal']['direction']}")
    print(f"   Confidence: {results['signal']['confidence']:.1f}/100")
    print(f"   {results['signal']['reason']}\n")