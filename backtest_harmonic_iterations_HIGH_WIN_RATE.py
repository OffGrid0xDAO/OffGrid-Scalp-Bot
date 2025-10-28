#!/usr/bin/env python3
"""
Backtest ALL 9 Harmonic Iterations (3-6-9 Convergence)

Tests each iteration's actual thresholds to get REAL performance data.
Uses the same backtest logic as fibonacci_ribbon_fine_tuner.py but with
our specific harmonic threshold combinations.

ALL parameters fine-tuned to Tesla's 3-6-9 harmonic convergence principles.
ALL iterations use FULL DSP: MTF FFT + Volume FFT + Fibonacci Levels
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fourier_strategy import FourierTradingStrategy
from fourier_strategy.fibonacci_ribbon_analyzer import FibonacciRibbonAnalyzer
from fourier_strategy.hyperliquid_adapter import HyperliquidDataAdapter
from src.reporting.chart_generator import ChartGenerator
from scipy.fft import fft, ifft

# Define all 9 harmonic iterations - ALL with FULL DSP (MTF + Volume FFT + Fib Levels)
# All values fine-tuned to 3-6-9 harmonic convergence
ITERATIONS = {
    1: {
        "name": "HARMONIC Trinity (3)",
        "compression": 84,      # 8+4=12 → 1+2=3 ✓
        "alignment": 84,        # 8+4=12 → 1+2=3 ✓
        "confluence": 60,       # 6+0=6 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.09,  # 0+9=9 ✓
        "fib_weight": 0.06,     # 0+6=6 ✓
        "description": "84/84/60 - Perfect Trinity (3+3+6) - Light DSP"
    },
    2: {
        "name": "HARMONIC Harmony (6)",
        "compression": 81,      # 8+1=9 ✓
        "alignment": 84,        # 8+4=12 → 1+2=3 ✓
        "confluence": 54,       # 5+4=9 ✓ (was 57)
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.12,  # 1+2=3 ✓
        "fib_weight": 0.09,     # 0+9=9 ✓
        "description": "81/84/54 - Harmony (9+3+9) - Balanced DSP"
    },
    3: {
        "name": "HARMONIC Resonance (9)",
        "compression": 81,      # 8+1=9 ✓
        "alignment": 81,        # 8+1=9 ✓
        "confluence": 54,       # 5+4=9 ✓ (was 55)
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.15,  # 1+5=6 ✓
        "fib_weight": 0.09,     # 0+9=9 ✓
        "description": "81/81/54 - Resonance (9+9+9) - Triple 9"
    },
    4: {
        "name": "HARMONIC Balance (3-6)",
        "compression": 78,      # 7+8=15 → 1+5=6 ✓
        "alignment": 78,        # 7+8=15 → 1+5=6 ✓
        "confluence": 54,       # 5+4=9 ✓ (was 51)
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.15,  # 1+5=6 ✓
        "fib_weight": 0.12,     # 1+2=3 ✓
        "description": "78/78/54 - Balance (6+6+9) - Medium DSP"
    },
    5: {
        "name": "HARMONIC Convergence (9-6)",
        "compression": 72,      # 7+2=9 ✓ (was 75)
        "alignment": 72,        # 7+2=9 ✓ (was 75)
        "confluence": 54,       # 5+4=9 ✓ (was 51)
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.18,  # 1+8=9 ✓ (was 0.21)
        "fib_weight": 0.15,     # 1+5=6 ✓
        "description": "72/72/54 - Convergence (9+9+9) - Strong DSP"
    },
    6: {
        "name": "HARMONIC Amplification (9-9)",
        "compression": 72,      # 7+2=9 ✓
        "alignment": 63,        # 6+3=9 ✓
        "confluence": 45,       # 4+5=9 ✓ (was 48)
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.21,  # 2+1=3 ✓
        "fib_weight": 0.18,     # 1+8=9 ✓
        "description": "72/63/45 - Amplification (9+9+9) - Heavy DSP"
    },
    7: {
        "name": "HARMONIC Power (9-MAX)",
        "compression": 63,      # 6+3=9 ✓ (was 69)
        "alignment": 72,        # 7+2=9 ✓
        "confluence": 45,       # 4+5=9 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.24,  # 2+4=6 ✓
        "fib_weight": 0.21,     # 2+1=3 ✓
        "description": "63/72/45 - Power (9+9+9) - Very Heavy DSP"
    },
    8: {
        "name": "HARMONIC Ultimate (9-9-9)",
        "compression": 63,      # 6+3=9 ✓
        "alignment": 63,        # 6+3=9 ✓
        "confluence": 45,       # 4+5=9 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.27,  # 2+7=9 ✓
        "fib_weight": 0.27,     # 2+7=9 ✓
        "description": "63/63/45 - Ultimate (9+9+9) - MAX DSP"
    },
    9: {
        "name": "HARMONIC Supreme (9-ULTRA)",
        "compression": 54,      # 5+4=9 ✓
        "alignment": 63,        # 6+3=9 ✓
        "confluence": 36,       # 3+6=9 ✓
        "min_signal_strength": 0.27,  # 2+7=9 ✓
        "use_volume_fft": True,
        "use_fib_levels": True,
        "volume_weight": 0.30,  # 3+0=3 ✓
        "fib_weight": 0.30,     # 3+0=3 ✓
        "description": "54/63/36 - Supreme (9+9+9) - ULTRA DSP"
    }
}

SCALPING_PARAMS = {
    # FFT Harmonic Parameters (3-6-9)
    'n_harmonics': 6,                # 6 → sum=6 ✓ (was 5)
    'noise_threshold': 0.27,         # 27 → 2+7=9 ✓ (was 0.25)
    'base_ema_period': 21,           # 21 → 2+1=3 ✓ (was 20)
    'correlation_threshold': 0.54,   # 54 → 5+4=9 ✓ (was 0.55)
    'min_signal_strength': 0.27,     # 27 → 2+7=9 ✓ (was 0.25)

    # Holding Period Parameters (3-6-9)
    'max_holding_periods': 27,       # 27 candles = 135 min → 2+7=9 ✓ (was 24)
    'min_holding_periods': 3,        # 3 candles = 15 minutes → sum=3 ✓

    # Position Sizing (HARMONIC)
    'position_size': 0.09,           # 9% of capital → sum=9 ✓ (was 0.10)
    'leverage': 27,                  # 27x → 2+7=9 ✓ (was 25x)

    # TP/SL for 27x leverage with 9% position (2.43x exposure multiplier)
    # Target: 3% capital gain, 1.2% capital loss
    # Exposure: 9% × 27 = 243% → 2.43x multiplier
    # TP needed: 3% / 2.43 = 1.235% → round to 1.26% (126 → 1+2+6=9 ✓)
    # SL needed: 1.2% / 2.43 = 0.494% → round to 0.54% (54 → 5+4=9 ✓)
    'tp_pct': 0.0126,   # 1.26% PRICE move = 3.06% capital gain (harmonic!)
    'sl_pct': 0.0054    # 0.54% PRICE move = 1.31% capital loss (harmonic!)
}


def apply_volume_fft(volume_series, n_harmonics=6):  # 6 → sum=6 ✓ (harmonic)
    """Apply FFT to volume data for momentum detection"""
    volume = volume_series.values
    n = len(volume)

    # Apply FFT
    fft_values = fft(volume)

    # Keep only top harmonics (harmonic percentile)
    magnitude = np.abs(fft_values)
    threshold = np.percentile(magnitude, 72)  # 72 → 7+2=9 ✓ (was 75)
    fft_filtered = fft_values.copy()
    fft_filtered[magnitude < threshold] = 0

    # Inverse FFT
    filtered_volume = np.abs(ifft(fft_filtered))

    # Calculate momentum score (normalized)
    volume_momentum = (filtered_volume - filtered_volume.min()) / (filtered_volume.max() - filtered_volume.min() + 1e-10)

    return pd.Series(volume_momentum, index=volume_series.index)


def calculate_fib_levels(df, lookback=144):  # 144 → 1+4+4=9 ✓ (Fibonacci number!)
    """Calculate Fibonacci retracement levels"""
    fib_levels = []

    for i in range(len(df)):
        if i < lookback:
            fib_levels.append(0.5)
            continue

        window = df.iloc[max(0, i-lookback):i+1]
        high = window['high'].max()
        low = window['low'].min()
        current_price = df['close'].iloc[i]

        # Calculate distance to nearest Fibonacci level
        levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        fib_prices = [low + (high - low) * level for level in levels]

        # Find closest level
        distances = [abs(current_price - fib_price) / (high - low + 1e-10) for fib_price in fib_prices]
        min_distance = min(distances)

        # Score: 1.0 = at level, 0.0 = far from level (harmonic multiplier)
        fib_score = 1.0 - min(min_distance * 18, 1.0)  # 18 → 1+8=9 ✓ (was 10)
        fib_levels.append(fib_score)

    return pd.Series(fib_levels, index=df.index)


def calculate_mtf_confluence(analysis_5m, analysis_15m, analysis_30m, df_5m, df_15m, df_30m):
    """Calculate multi-timeframe confluence score"""

    # Resample 15m signals to 5m
    confluence_15m = analysis_15m['confluence'].reindex(df_5m.index, method='ffill')
    alignment_15m = analysis_15m['alignment'].reindex(df_5m.index, method='ffill')

    # Resample 30m signals to 5m
    confluence_30m = analysis_30m['confluence'].reindex(df_5m.index, method='ffill')
    alignment_30m = analysis_30m['alignment'].reindex(df_5m.index, method='ffill')

    # Get 5m signals
    confluence_5m = analysis_5m['confluence']
    alignment_5m = analysis_5m['alignment']

    # Calculate multi-timeframe confluence
    # Score = average of all timeframe confluences, weighted by alignment agreement
    mtf_score = (confluence_5m + confluence_15m + confluence_30m) / 3

    # Boost when all timeframes agree on direction
    alignment_agreement = (
        (np.sign(alignment_5m) == np.sign(alignment_15m)) &
        (np.sign(alignment_5m) == np.sign(alignment_30m))
    ).astype(float)

    # Add 18 points when all timeframes align (harmonic: 18 → 1+8=9 ✓)
    mtf_score = mtf_score + (alignment_agreement * 18)  # was 20

    return mtf_score


def analyze_ribbons_for_iteration(df, iter_config):
    """Analyze Fibonacci ribbons for a specific iteration"""

    # Initialize analyzers
    fourier_strategy = FourierTradingStrategy(
        n_harmonics=SCALPING_PARAMS['n_harmonics'],
        noise_threshold=SCALPING_PARAMS['noise_threshold'],
        base_ema_period=SCALPING_PARAMS['base_ema_period'],
        correlation_threshold=SCALPING_PARAMS['correlation_threshold'],
        min_signal_strength=iter_config['min_signal_strength'],
        max_holding_periods=SCALPING_PARAMS['max_holding_periods']
    )

    fib_analyzer = FibonacciRibbonAnalyzer(
        n_harmonics=SCALPING_PARAMS['n_harmonics'],
        noise_threshold=SCALPING_PARAMS['noise_threshold']
    )

    # Run analyses
    fourier_results = fourier_strategy.run(df, run_backtest=False, verbose=False)
    fib_results = fib_analyzer.analyze(df)

    analysis = {
        'fourier_df': fourier_results['output_df'],
        'fib_signals': fib_results['signals'],
        'compression': fib_results['signals']['fibonacci_compression'],
        'alignment': fib_results['signals']['fibonacci_alignment'],
        'confluence': fib_results['signals']['fibonacci_confluence']
    }

    # Add Volume FFT if enabled
    if iter_config.get('use_volume_fft', False):
        print(f"   🌊 Applying Volume FFT (weight: {iter_config['volume_weight']})")
        analysis['volume_momentum'] = apply_volume_fft(df['volume'], SCALPING_PARAMS['n_harmonics'])
    else:
        analysis['volume_momentum'] = pd.Series(0.5, index=df.index)

    # Add Fibonacci levels if enabled
    if iter_config.get('use_fib_levels', False):
        print(f"   📐 Calculating Fibonacci price levels (weight: {iter_config['fib_weight']})")
        analysis['fib_proximity'] = calculate_fib_levels(df)
    else:
        analysis['fib_proximity'] = pd.Series(0.5, index=df.index)

    return analysis


def backtest_iteration(iter_num, iter_config, analysis):
    """Backtest a single iteration with its specific thresholds"""

    print(f"\n{'='*80}")
    print(f"  🧪 TESTING ITERATION {iter_num}: {iter_config['name']}")
    print(f"{'='*80}")
    print(f"  {iter_config['description']}")
    print(f"  Compression: {iter_config['compression']}")
    print(f"  Alignment: {iter_config['alignment']}")
    print(f"  Confluence: {iter_config['confluence']}")

    base_df = analysis['fourier_df'].copy()
    compression = analysis['compression']
    alignment = analysis['alignment']
    confluence = analysis['confluence']
    volume_momentum = analysis['volume_momentum']
    fib_proximity = analysis['fib_proximity']

    # Add MTF confluence to dataframe
    if 'mtf_confluence' in analysis:
        base_df['mtf_confluence'] = analysis['mtf_confluence']
    else:
        base_df['mtf_confluence'] = confluence  # Fallback to single TF

    comp_thresh = iter_config['compression']
    align_thresh = iter_config['alignment']
    conf_thresh = iter_config['confluence']
    use_volume = iter_config.get('use_volume_fft', False)
    use_fib = iter_config.get('use_fib_levels', False)
    volume_weight = iter_config.get('volume_weight', 0.0)
    fib_weight = iter_config.get('fib_weight', 0.0)

    # Backtest parameters
    capital = 10000.0
    position = 0
    trades = []
    entry_price = 0
    entry_time = None
    entry_direction = None
    tp_price = 0
    sl_price = 0
    lookback = 50
    max_hold = SCALPING_PARAMS['max_holding_periods']
    min_hold = SCALPING_PARAMS['min_holding_periods']
    tp_pct = SCALPING_PARAMS['tp_pct']
    sl_pct = SCALPING_PARAMS['sl_pct']

    # Track equity curve
    equity_curve = [capital]
    equity_times = [base_df.index[lookback]]

    for i in range(lookback, len(base_df)):
        current_time = base_df.index[i]
        current_price = base_df['close'].iloc[i]

        # Get signals
        comp = compression.iloc[i]
        align = alignment.iloc[i]
        conf = confluence.iloc[i]
        fourier_signal = base_df['composite_signal'].iloc[i]
        vol_momentum = volume_momentum.iloc[i]
        fib_prox = fib_proximity.iloc[i]

        # Get multi-timeframe confluence (if available)
        mtf_conf = base_df['mtf_confluence'].iloc[i] if 'mtf_confluence' in base_df.columns else conf

        # Enhanced signal with Volume FFT + Fib levels + MTF confluence
        enhanced_signal = fourier_signal
        if use_volume:
            # Boost signal when volume momentum confirms (harmonic threshold)
            vol_boost = (vol_momentum - 0.54) * volume_weight  # 54 → 5+4=9 ✓ (was 0.5)
            enhanced_signal += vol_boost
        if use_fib:
            # Boost signal when price near Fibonacci level
            fib_boost = fib_prox * fib_weight
            enhanced_signal += fib_boost

        # Boost signal when multi-timeframe confluence is high (harmonic)
        if mtf_conf > 81:  # 81 → 8+1=9 ✓ (was 80)
            enhanced_signal *= 1.18  # 18% boost → 1+8=9 ✓ (was 1.2)

        # Entry conditions
        should_enter_long = (
            position == 0 and
            comp > comp_thresh and
            align > align_thresh and
            conf > conf_thresh and
            enhanced_signal > iter_config['min_signal_strength']
        )

        should_enter_short = (
            position == 0 and
            comp > comp_thresh and
            align < -align_thresh and
            conf > conf_thresh and
            enhanced_signal < -iter_config['min_signal_strength']
        )

        # Exit conditions - PROPER TP/SL BASED
        should_exit = False
        exit_reason = None
        if position != 0:
            holding_periods = i - base_df.index.get_loc(entry_time)

            # CRITICAL FIX: Don't check exit on the same candle we entered
            # This prevents immediate exits when entry candle's high/low touched TP/SL
            if holding_periods == 0:
                # Skip all exit checks on entry candle
                should_exit = False
            else:
                # Get high/low for this candle
                current_high = base_df['high'].iloc[i]
                current_low = base_df['low'].iloc[i]

                # Check TP/SL using high/low (not just close)
                # This is more realistic - checks if price TOUCHED the level during the candle
                if position == 1:  # Long position
                    # Check if high touched TP
                    if current_high >= tp_price:
                        should_exit = True
                        exit_reason = 'TP'
                        current_price = tp_price  # Exit at TP price
                    # Check if low touched SL
                    elif current_low <= sl_price:
                        should_exit = True
                        exit_reason = 'SL'
                        current_price = sl_price  # Exit at SL price
                else:  # Short position
                    # Check if low touched TP
                    if current_low <= tp_price:
                        should_exit = True
                        exit_reason = 'TP'
                        current_price = tp_price  # Exit at TP price
                    # Check if high touched SL
                    elif current_high >= sl_price:
                        should_exit = True
                        exit_reason = 'SL'
                        current_price = sl_price  # Exit at SL price

                # Only check time-based exits AFTER minimum holding period
                if not should_exit and holding_periods >= min_hold:
                    # Exit on max holding period
                    if holding_periods >= max_hold:
                        should_exit = True
                        exit_reason = 'MAX_HOLD'
                    # Exit on strong signal reversal (harmonic threshold)
                    elif position == 1 and enhanced_signal < -0.27:  # 27 → 2+7=9 ✓ (was 0.3)
                        should_exit = True
                        exit_reason = 'SIGNAL_REVERSAL'
                    elif position == -1 and enhanced_signal > 0.27:  # 27 → 2+7=9 ✓ (was 0.3)
                        should_exit = True
                        exit_reason = 'SIGNAL_REVERSAL'
                    # Exit on compression breakdown (harmonic threshold)
                    elif comp < 45:  # 45 → 4+5=9 ✓ (was 50)
                        should_exit = True
                        exit_reason = 'COMPRESSION_BREAKDOWN'

        # Execute exit
        if should_exit and position != 0:
            if position == 1:
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100

            pnl = capital * 0.09 * (pnl_pct / 100)  # 9% position size (harmonic)
            capital += pnl

            trade_data = {
                'entry_time': str(entry_time) if hasattr(entry_time, 'isoformat') else entry_time,
                'exit_time': str(current_time) if hasattr(current_time, 'isoformat') else current_time,
                'direction': entry_direction,
                'entry_price': float(entry_price),
                'exit_price': float(current_price),
                'tp_price': float(tp_price),
                'sl_price': float(sl_price),
                'pnl_pct': float(pnl_pct),
                'pnl': float(pnl),
                'holding_periods': int(holding_periods),
                'exit_reason': exit_reason,
                'total_pnl_pct': float(pnl_pct)  # For chart compatibility
            }
            trades.append(trade_data)

            # Reset position
            position = 0
            tp_price = 0
            sl_price = 0

        # Execute entry (and calculate TP/SL)
        if should_enter_long:
            position = 1
            entry_price = current_price
            entry_time = current_time
            entry_direction = 'LONG'
            # Set TP/SL for long
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
        elif should_enter_short:
            position = -1
            entry_price = current_price
            entry_time = current_time
            entry_direction = 'SHORT'
            # Set TP/SL for short
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)

        # Track equity
        equity_curve.append(capital)
        equity_times.append(current_time)

    # Calculate metrics
    if len(trades) == 0:
        print(f"\n  ⚠️  NO TRADES - Thresholds too restrictive!")
        return {
            'iteration': iter_num,
            'name': iter_config['name'],
            'thresholds': f"{comp_thresh}/{align_thresh}/{conf_thresh}",
            'return_17d': 0,
            'monthly_projection': 0,
            'sharpe': 0,
            'win_rate': 0,
            'max_dd': 0,
            'num_trades': 0,
            'trades_per_day': 0,
            'max_risk_per_trade_pct': 0
        }

    trades_df = pd.DataFrame(trades)

    total_return_pct = (capital - 10000) / 10000 * 100
    winning_trades = trades_df[trades_df['pnl_pct'] > 0]
    losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
    win_rate = len(winning_trades) / len(trades_df) * 100

    # Sharpe ratio
    returns = trades_df['pnl_pct'].values
    if len(returns) > 1 and returns.std() > 0:
        sharpe = returns.mean() / returns.std() * np.sqrt(252)
    else:
        sharpe = 0

    # Max drawdown
    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.expanding().max()
    drawdown = (equity_series - rolling_max) / rolling_max * 100
    max_dd = drawdown.min()

    # Days calculation
    days = (base_df.index[-1] - base_df.index[0]).days

    # Trades per day
    trades_per_day = len(trades) / days

    # Exit reason analysis
    exit_reasons = {}
    for trade in trades:
        reason = trade.get('exit_reason', 'UNKNOWN')
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    # Average holding time
    avg_holding = trades_df['holding_periods'].mean() if len(trades_df) > 0 else 0
    avg_holding_minutes = avg_holding * 5

    # Monthly projection (WITHOUT leverage multiplier)
    monthly_return_actual = total_return_pct * (30 / days)

    # Risk analysis with 27x leverage (HARMONIC)
    position_size_pct = 9  # 9% of capital per trade (harmonic: sum=9 ✓)
    sl_price_pct = SCALPING_PARAMS['sl_pct'] * 100  # Convert to percentage
    leverage_used = 27  # 27x → 2+7=9 ✓ (harmonic)
    exposure_multiplier = (position_size_pct / 100) * leverage_used  # 0.09 × 27 = 2.43
    max_risk_per_trade = exposure_multiplier * (sl_price_pct / 100)
    max_risk_pct = max_risk_per_trade * 100

    print(f"\n  📊 RESULTS:")
    print(f"     Return ({days}d):       {total_return_pct:.2f}%")
    print(f"     Monthly Projection:     {monthly_return_actual:.2f}%")
    print(f"     Sharpe Ratio:           {sharpe:.2f}")
    print(f"     Win Rate:               {win_rate:.1f}%")
    print(f"     Max Drawdown:           {max_dd:.2f}%")
    print(f"     Trades:                 {len(trades)}")
    print(f"     Trades/Day:             {trades_per_day:.2f}")
    print(f"     Avg Hold Time:          {avg_holding:.1f} candles ({avg_holding_minutes:.0f} min)")
    print(f"     Max Risk per Trade:     {max_risk_pct:.2f}% (SAFE ✅)" if max_risk_pct < 5 else f"     Max Risk per Trade:     {max_risk_pct:.2f}% (HIGH ⚠️)")
    print(f"     Exit Reasons:           {exit_reasons}")

    return {
        'iteration': iter_num,
        'name': iter_config['name'],
        'thresholds': f"{comp_thresh}/{align_thresh}/{conf_thresh}",
        'return_17d': total_return_pct,
        'monthly_projection': monthly_return_actual,
        'sharpe': sharpe,
        'win_rate': win_rate,
        'max_dd': max_dd,
        'num_trades': len(trades),
        'trades_per_day': trades_per_day,
        'max_risk_per_trade_pct': max_risk_pct,
        'trades': trades  # Include trades for chart generation
    }


def main():
    print("\n" + "="*80)
    print("  🎯 BACKTEST ALL 9 HARMONIC ITERATIONS (3-6-9 CONVERGENCE)")
    print("="*80)
    print("\nUsing FULL DSP POWER:")
    print("  ✅ Multi-Timeframe FFT Analysis (5m + 15m + 30m)")
    print("  ✅ Fibonacci Ribbon FFT (11 EMAs)")
    print("  ✅ Volume FFT Confirmation")
    print("  ✅ Fibonacci Price Levels")

    # Fetch MULTI-TIMEFRAME data
    print("\n📊 Fetching 17 days of MULTI-TIMEFRAME data...")
    adapter = HyperliquidDataAdapter(symbol='ETH')

    print("  ⚡ Fetching 5m data...")
    df_5m = adapter.fetch_ohlcv(interval='5m', days_back=17, use_checkpoint=False)
    print(f"     ✅ {len(df_5m)} candles")

    print("  ⚡ Fetching 15m data...")
    df_15m = adapter.fetch_ohlcv(interval='15m', days_back=17, use_checkpoint=False)
    print(f"     ✅ {len(df_15m)} candles")

    print("  ⚡ Fetching 30m data...")
    df_30m = adapter.fetch_ohlcv(interval='30m', days_back=17, use_checkpoint=False)
    print(f"     ✅ {len(df_30m)} candles")

    print(f"\n✅ All timeframes fetched!")

    # Analyze ALL timeframes
    print("\n🔬 Multi-Timeframe Ribbon Analysis...")

    # Analyze each timeframe
    tf_analyses = {}
    for tf_name, df_tf in [('5m', df_5m), ('15m', df_15m), ('30m', df_30m)]:
        print(f"\n   📊 Analyzing {tf_name} ribbons...")
        # We'll do simple analysis for 15m and 30m without full iteration config
        analysis_tf = analyze_ribbons_for_iteration(df_tf, ITERATIONS[1])
        tf_analyses[tf_name] = analysis_tf

    # Backtest each iteration with its specific thresholds + MTF confluence
    all_results = []
    all_trades_by_iteration = {}

    for iter_num in sorted(ITERATIONS.keys()):
        config = ITERATIONS[iter_num]

        print(f"\n{'='*80}")
        print(f"  🔬 Analyzing Iteration {iter_num} with MULTI-TIMEFRAME")
        print(f"{'='*80}")

        # Analyze 5m with full config (including Volume FFT + Fib for iterations 4-6)
        analysis_5m = analyze_ribbons_for_iteration(df_5m, config)

        # Add multi-timeframe confluence signals
        # Resample 15m and 30m signals to 5m timeframe
        analysis_5m['mtf_confluence'] = calculate_mtf_confluence(
            analysis_5m,
            tf_analyses['15m'],
            tf_analyses['30m'],
            df_5m, df_15m, df_30m
        )

        result = backtest_iteration(iter_num, config, analysis_5m)
        all_results.append(result)

        # Store analysis for chart generation
        all_trades_by_iteration[iter_num] = {
            'config': config,
            'analysis': analysis_5m,
            'result': result
        }

    # Print comparison table
    print("\n" + "="*80)
    print("  📊 ITERATION COMPARISON TABLE")
    print("="*80)
    print("\n| Iter | Thresholds | Trades | Return (17d) | Monthly | Sharpe | Win Rate | Risk/Trade |")
    print("|------|------------|--------|--------------|---------|--------|----------|------------|")

    for r in all_results:
        risk_str = f"{r['max_risk_per_trade_pct']:.2f}%"
        print(f"| {r['iteration']} | {r['thresholds']:>10} | {int(r['num_trades']):>6} | "
              f"{r['return_17d']:>11.2f}% | {r['monthly_projection']:>6.2f}% | "
              f"{r['sharpe']:>5.2f} | {r['win_rate']:>7.1f}% | {risk_str:>10} |")

    # Save results (without trades to avoid serialization issues)
    output_file = 'trading_data/harmonic_iterations_backtest.json'
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    # Create serializable version without trades
    serializable_results = []
    for r in all_results:
        r_copy = r.copy()
        if 'trades' in r_copy:
            r_copy['num_trades'] = len(r_copy['trades'])
            del r_copy['trades']  # Remove trades for JSON
        serializable_results.append(r_copy)

    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'leverage': 25,
            'position_size': 0.06,
            'days_tested': 17,
            'iterations': serializable_results
        }, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")

    # Return data for chart generation
    return df_5m, all_results, all_trades_by_iteration

    # Find best iteration
    valid_results = [r for r in all_results if r['num_trades'] > 0]

    if valid_results:
        best_return = max(valid_results, key=lambda x: x['monthly_projection'])
        best_sharpe = max(valid_results, key=lambda x: x['sharpe'])

        print("\n" + "="*80)
        print("  🏆 RECOMMENDATIONS")
        print("="*80)
        print(f"\n  Best Monthly Return: Iteration {best_return['iteration']} ({best_return['monthly_projection']:.2f}%)")
        print(f"  Best Sharpe Ratio:   Iteration {best_sharpe['iteration']} ({best_sharpe['sharpe']:.2f})")
        print(f"\n  💡 Recommended: Start with Iteration {best_sharpe['iteration']}, progress based on results")
    else:
        print("\n⚠️  WARNING: No iterations generated trades! Thresholds may be too restrictive.")


if __name__ == '__main__':
    df_5m, results, trades_by_iter = main()

    # Generate charts for best iterations
    print("\n" + "="*80)
    print("  📊 GENERATING CHARTS")
    print("="*80)

    chart_gen = ChartGenerator()
    valid_results = [r for r in results if r['num_trades'] > 0]

    if valid_results:
        import webbrowser

        # Generate chart for best Sharpe iteration
        best_sharpe_iter = max(valid_results, key=lambda x: x['sharpe'])
        iter_num = best_sharpe_iter['iteration']

        print(f"\n📈 Generating chart for Iteration {iter_num} (Best Sharpe: {best_sharpe_iter['sharpe']:.2f})...")

        # Convert trades with pandas Timestamps to datetime strings for chart
        trades_for_chart = []
        for trade in best_sharpe_iter['trades']:
            trade_copy = trade.copy()
            # Parse string timestamps back to pandas Timestamp for chart
            trade_copy['entry_time'] = pd.Timestamp(trade_copy['entry_time'])
            trade_copy['exit_time'] = pd.Timestamp(trade_copy['exit_time'])
            trades_for_chart.append(trade_copy)

        # Prepare df with timestamp column and required indicators
        df_for_chart = df_5m.copy()
        df_for_chart['timestamp'] = df_for_chart.index

        # Add missing columns for chart compatibility
        if 'volume_status' not in df_for_chart.columns:
            df_for_chart['volume_status'] = 'neutral'
        if 'fibonacci_confluence' not in df_for_chart.columns:
            df_for_chart['fibonacci_confluence'] = 50.0
        if 'rsi' not in df_for_chart.columns:
            df_for_chart['rsi'] = 50.0
        if 'stoch_k' not in df_for_chart.columns:
            df_for_chart['stoch_k'] = 50.0
        if 'stoch_d' not in df_for_chart.columns:
            df_for_chart['stoch_d'] = 50.0

        chart_path = chart_gen.create_3way_comparison_chart(
            df=df_for_chart,
            optimal_trades=[],  # No optimal trades for this analysis
            backtest_trades=trades_for_chart,
            actual_trades=None,
            symbol='ETH',
            timeframe='5m',
            candles_to_show=min(1000, len(df_5m))
        )

        print(f"✅ Chart saved: {chart_path}")
        webbrowser.open(f'file://{Path(chart_path).absolute()}')

        # Generate chart for best return iteration
        best_return_iter = max(valid_results, key=lambda x: x['monthly_projection'])
        if best_return_iter['iteration'] != best_sharpe_iter['iteration']:
            iter_num = best_return_iter['iteration']

            print(f"\n📈 Generating chart for Iteration {iter_num} (Best Return: {best_return_iter['monthly_projection']:.2f}%)...")

            trades_for_chart = []
            for trade in best_return_iter['trades']:
                trade_copy = trade.copy()
                trade_copy['entry_time'] = pd.Timestamp(trade_copy['entry_time'])
                trade_copy['exit_time'] = pd.Timestamp(trade_copy['exit_time'])
                trades_for_chart.append(trade_copy)

            df_for_chart = df_5m.copy()
            df_for_chart['timestamp'] = df_for_chart.index

            # Add missing columns for chart compatibility
            if 'volume_status' not in df_for_chart.columns:
                df_for_chart['volume_status'] = 'neutral'
            if 'fibonacci_confluence' not in df_for_chart.columns:
                df_for_chart['fibonacci_confluence'] = 50.0
            if 'rsi' not in df_for_chart.columns:
                df_for_chart['rsi'] = 50.0
            if 'stoch_k' not in df_for_chart.columns:
                df_for_chart['stoch_k'] = 50.0
            if 'stoch_d' not in df_for_chart.columns:
                df_for_chart['stoch_d'] = 50.0

            chart_path = chart_gen.create_3way_comparison_chart(
                df=df_for_chart,
                optimal_trades=[],
                backtest_trades=trades_for_chart,
                actual_trades=None,
                symbol='ETH',
                timeframe='5m',
                candles_to_show=min(1000, len(df_5m))
            )

            print(f"✅ Chart saved: {chart_path}")
            webbrowser.open(f'file://{Path(chart_path).absolute()}')

        print("\n🎉 Charts opened in browser!")
