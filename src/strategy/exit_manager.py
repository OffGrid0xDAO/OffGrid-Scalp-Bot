#!/usr/bin/env python3
"""
Exit Manager - Professional Day Trading Exit System

Implements sophisticated exit strategy optimized for 2-3 trades/day:

CORE EXITS:
- Partial exits at multiple profit levels (40% @ 1.5%, 30% @ 3%, 30% @ 5%)
- EMA-based stop loss
- Trailing stop using EMA20
- Time-based exits (max 12 candles)

PROFESSIONAL INDICATOR EXITS (NEW):
- Stochastic Reversal: Exit when momentum reverses in extreme zones (>80 or <20)
- Bollinger Band Reversal: Exit when price reaches opposite band (overbought/oversold)
- VWAP Cross: Exit when price crosses back through VWAP (losing institutional support)

RIBBON EXITS:
- Compression increase (ribbons tightening after expansion)
- Yellow EMA break (price crosses key support/resistance)

MFE/MAE TRACKING:
- Maximum Favorable Excursion (best profit reached)
- Maximum Adverse Excursion (worst drawdown)
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional


class ExitManager:
    """
    Manage trade exits with partial profit taking and dynamic stops

    Exit Strategy (from research):
    - Take 50% profit at +1% (55.3% probability)
    - Take 30% profit at +2% (36.6% probability)
    - Take 20% profit at +3% (let winners run)
    - Stop loss: 0.5% below EMA20 for longs, above for shorts
    - Trailing stop: Use EMA20 once +2% profit reached
    """

    def __init__(self, params_file: str = None):
        """
        Initialize exit manager

        Args:
            params_file: Path to strategy parameters JSON file
        """
        if params_file is None:
            params_file = Path(__file__).parent / 'strategy_params.json'

        with open(params_file, 'r') as f:
            self.params = json.load(f)

        self.exit_strategy = self.params['exit_strategy']

    def calculate_exit_levels(self, entry_price: float, direction: str, df: pd.DataFrame = None) -> Dict:
        """
        Calculate all exit levels for a trade

        Args:
            entry_price: Entry price
            direction: 'long' or 'short'
            df: DataFrame with latest data (for EMA-based stops)

        Returns:
            dict with:
                - stop_loss: float
                - take_profit_1: float (1% target)
                - take_profit_2: float (2% target)
                - take_profit_3: float (3% target)
                - tp_sizes: list of position sizes to exit
        """
        tp_levels = self.exit_strategy['take_profit_levels']
        tp_sizes = self.exit_strategy['take_profit_sizes']
        stop_loss_pct = self.exit_strategy['stop_loss_pct']

        if direction == 'long':
            # Long exits
            tp1 = entry_price * (1 + tp_levels[0] / 100)
            tp2 = entry_price * (1 + tp_levels[1] / 100)
            tp3 = entry_price * (1 + tp_levels[2] / 100)

            # Stop loss: Use EMA20 if available, otherwise fixed %
            if df is not None and 'MMA20_value' in df.columns:
                ema20 = df.iloc[-1]['MMA20_value']
                stop_loss = ema20 * (1 - stop_loss_pct / 100)
                # Don't let stop be above entry
                stop_loss = min(stop_loss, entry_price * (1 - stop_loss_pct / 100))
            else:
                stop_loss = entry_price * (1 - stop_loss_pct / 100)

        else:
            # Short exits
            tp1 = entry_price * (1 - tp_levels[0] / 100)
            tp2 = entry_price * (1 - tp_levels[1] / 100)
            tp3 = entry_price * (1 - tp_levels[2] / 100)

            # Stop loss: Use EMA20 if available, otherwise fixed %
            if df is not None and 'MMA40_value' in df.columns:
                ema20 = df.iloc[-1]['MMA40_value']
                stop_loss = ema20 * (1 + stop_loss_pct / 100)
                # Don't let stop be below entry
                stop_loss = max(stop_loss, entry_price * (1 + stop_loss_pct / 100))
            else:
                stop_loss = entry_price * (1 + stop_loss_pct / 100)

        return {
            'stop_loss': stop_loss,
            'take_profit_1': tp1,
            'take_profit_2': tp2,
            'take_profit_3': tp3,
            'tp_sizes': tp_sizes,
            'tp_levels': tp_levels
        }

    def check_exit(self, trade: Dict, current_candle: pd.Series, candles_held: int = 0) -> Dict:
        """
        Check if trade should exit on current candle

        Args:
            trade: Trade dict with entry_price, direction, remaining_size, exits_taken
            current_candle: Current candle data
            candles_held: Number of candles since entry

        Returns:
            dict with:
                - should_exit: bool
                - exit_type: 'stop_loss', 'take_profit_1', 'take_profit_2', 'take_profit_3', 'time_exit'
                - exit_price: float
                - exit_size: float (% of remaining position)
                - profit_pct: float
                - reason: str
        """
        entry_price = trade['entry_price']
        direction = trade['direction']
        remaining_size = trade.get('remaining_size', 100)
        exits_taken = trade.get('exits_taken', [])

        current_price = current_candle['close']
        high = current_candle['high']
        low = current_candle['low']

        # Get exit levels
        exit_levels = trade.get('exit_levels')
        if exit_levels is None:
            # Calculate on first check
            df_single = pd.DataFrame([current_candle])
            exit_levels = self.calculate_exit_levels(entry_price, direction, df_single)
            trade['exit_levels'] = exit_levels

        result = {
            'should_exit': False,
            'exit_type': None,
            'exit_price': current_price,
            'exit_size': 0,
            'profit_pct': 0,
            'reason': ''
        }

        # Calculate current profit
        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price * 100
            max_profit_pct = (high - entry_price) / entry_price * 100
            max_loss_pct = (low - entry_price) / entry_price * 100
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100
            max_profit_pct = (entry_price - low) / entry_price * 100
            max_loss_pct = (entry_price - high) / entry_price * 100

        result['profit_pct'] = profit_pct

        # CHECK 1: Stop Loss
        stop_loss = exit_levels['stop_loss']
        if direction == 'long':
            if low <= stop_loss:
                result['should_exit'] = True
                result['exit_type'] = 'stop_loss'
                result['exit_price'] = stop_loss
                result['exit_size'] = remaining_size
                result['profit_pct'] = (stop_loss - entry_price) / entry_price * 100
                result['reason'] = f'Stop loss hit: {low:.2f} <= {stop_loss:.2f}'
                return result
        else:
            if high >= stop_loss:
                result['should_exit'] = True
                result['exit_type'] = 'stop_loss'
                result['exit_price'] = stop_loss
                result['exit_size'] = remaining_size
                result['profit_pct'] = (entry_price - stop_loss) / entry_price * 100
                result['reason'] = f'Stop loss hit: {high:.2f} >= {stop_loss:.2f}'
                return result

        # CHECK 2: Take Profit Levels (check in order: TP3, TP2, TP1)
        # Check highest targets first since price might hit multiple in one candle

        tp_levels = exit_levels['tp_levels']
        tp_sizes = exit_levels['tp_sizes']

        # TP3 (3% target - 20% position)
        if 'tp3' not in exits_taken:
            tp3 = exit_levels['take_profit_3']
            if direction == 'long':
                if high >= tp3:
                    result['should_exit'] = True
                    result['exit_type'] = 'take_profit_3'
                    result['exit_price'] = tp3
                    result['exit_size'] = tp_sizes[2]
                    result['profit_pct'] = tp_levels[2]
                    result['reason'] = f'TP3 hit: {high:.2f} >= {tp3:.2f} (+{tp_levels[2]}%)'
                    return result
            else:
                if low <= tp3:
                    result['should_exit'] = True
                    result['exit_type'] = 'take_profit_3'
                    result['exit_price'] = tp3
                    result['exit_size'] = tp_sizes[2]
                    result['profit_pct'] = tp_levels[2]
                    result['reason'] = f'TP3 hit: {low:.2f} <= {tp3:.2f} (+{tp_levels[2]}%)'
                    return result

        # TP2 (2% target - 30% position)
        if 'tp2' not in exits_taken:
            tp2 = exit_levels['take_profit_2']
            if direction == 'long':
                if high >= tp2:
                    result['should_exit'] = True
                    result['exit_type'] = 'take_profit_2'
                    result['exit_price'] = tp2
                    result['exit_size'] = tp_sizes[1]
                    result['profit_pct'] = tp_levels[1]
                    result['reason'] = f'TP2 hit: {high:.2f} >= {tp2:.2f} (+{tp_levels[1]}%)'

                    # Enable trailing stop after TP2
                    if self.exit_strategy['trailing_stop_enabled']:
                        trade['use_trailing_stop'] = True

                    return result
            else:
                if low <= tp2:
                    result['should_exit'] = True
                    result['exit_type'] = 'take_profit_2'
                    result['exit_price'] = tp2
                    result['exit_size'] = tp_sizes[1]
                    result['profit_pct'] = tp_levels[1]
                    result['reason'] = f'TP2 hit: {low:.2f} <= {tp2:.2f} (+{tp_levels[1]}%)'

                    # Enable trailing stop after TP2
                    if self.exit_strategy['trailing_stop_enabled']:
                        trade['use_trailing_stop'] = True

                    return result

        # TP1 (1% target - 50% position)
        if 'tp1' not in exits_taken:
            tp1 = exit_levels['take_profit_1']
            if direction == 'long':
                if high >= tp1:
                    result['should_exit'] = True
                    result['exit_type'] = 'take_profit_1'
                    result['exit_price'] = tp1
                    result['exit_size'] = tp_sizes[0]
                    result['profit_pct'] = tp_levels[0]
                    result['reason'] = f'TP1 hit: {high:.2f} >= {tp1:.2f} (+{tp_levels[0]}%)'
                    return result
            else:
                if low <= tp1:
                    result['should_exit'] = True
                    result['exit_type'] = 'take_profit_1'
                    result['exit_price'] = tp1
                    result['exit_size'] = tp_sizes[0]
                    result['profit_pct'] = tp_levels[0]
                    result['reason'] = f'TP1 hit: {low:.2f} <= {tp1:.2f} (+{tp_levels[0]}%)'
                    return result

        # CHECK 3: Trailing Stop (if enabled and in profit)
        if trade.get('use_trailing_stop') and 'MMA20_value' in current_candle:
            trailing_ema_period = self.exit_strategy['trailing_stop_ema']
            ema_col = f'MMA{trailing_ema_period}_value'

            if ema_col in current_candle:
                trailing_stop = current_candle[ema_col]

                if direction == 'long':
                    if low <= trailing_stop:
                        result['should_exit'] = True
                        result['exit_type'] = 'trailing_stop'
                        result['exit_price'] = trailing_stop
                        result['exit_size'] = remaining_size
                        result['profit_pct'] = (trailing_stop - entry_price) / entry_price * 100
                        result['reason'] = f'Trailing stop hit: {low:.2f} <= EMA{trailing_ema_period} {trailing_stop:.2f}'
                        return result
                else:
                    if high >= trailing_stop:
                        result['should_exit'] = True
                        result['exit_type'] = 'trailing_stop'
                        result['exit_price'] = trailing_stop
                        result['exit_size'] = remaining_size
                        result['profit_pct'] = (entry_price - trailing_stop) / entry_price * 100
                        result['reason'] = f'Trailing stop hit: {high:.2f} >= EMA{trailing_ema_period} {trailing_stop:.2f}'
                        return result

        # CHECK 3.5: Compression Increase Exit (Ribbon Strategy)
        # STAY IN during expansion (the big move)
        # EXIT when compression increases = move exhausting, ribbons tightening again
        compression_increase = self._check_compression_increase(current_candle)
        if compression_increase and profit_pct > 0.5:  # Only if in profit
            result['should_exit'] = True
            result['exit_type'] = 'compression_increase'
            result['exit_price'] = current_price
            result['exit_size'] = remaining_size
            result['reason'] = f'Ribbons compressing - move exhausting (profit: {profit_pct:.2f}%)'
            return result

        # CHECK 3.6: Yellow EMA Support/Resistance Break (Ribbon Strategy)
        # Exit if price crosses below yellow EMA (20 or 21) for longs, above for shorts
        yellow_ema_break = self._check_yellow_ema_break(current_candle, direction, entry_price)
        if yellow_ema_break:
            result['should_exit'] = True
            result['exit_type'] = 'yellow_ema_break'
            result['exit_price'] = current_price
            result['exit_size'] = remaining_size
            result['reason'] = yellow_ema_break
            return result

        # CHECK 3.7: Stochastic Reversal (NEW - Professional Exit Signal)
        # Exit when Stochastic signals momentum reversal in extreme zones
        if self.exit_strategy.get('use_stochastic_exit', True):
            stoch_reversal = self._check_stochastic_reversal(current_candle, direction, profit_pct)
            if stoch_reversal:
                result['should_exit'] = True
                result['exit_type'] = 'stochastic_reversal'
                result['exit_price'] = current_price
                result['exit_size'] = remaining_size
                result['reason'] = stoch_reversal
                return result

        # CHECK 3.8: Bollinger Band Reversal (NEW - Volatility Exit)
        # Exit when price reaches opposite Bollinger Band (overbought/oversold)
        if self.exit_strategy.get('use_bollinger_exit', True):
            bb_reversal = self._check_bollinger_reversal(current_candle, direction, profit_pct)
            if bb_reversal:
                result['should_exit'] = True
                result['exit_type'] = 'bollinger_reversal'
                result['exit_price'] = current_price
                result['exit_size'] = remaining_size
                result['reason'] = bb_reversal
                return result

        # CHECK 3.9: VWAP Cross (NEW - Institutional Exit)
        # Exit when price crosses back through VWAP (losing institutional support/resistance)
        if self.exit_strategy.get('use_vwap_exit', True):
            vwap_cross = self._check_vwap_cross(current_candle, direction, profit_pct)
            if vwap_cross:
                result['should_exit'] = True
                result['exit_type'] = 'vwap_cross'
                result['exit_price'] = current_price
                result['exit_size'] = remaining_size
                result['reason'] = vwap_cross
                return result

        # CHECK 4: Time-based exit (optional)
        if self.exit_strategy['use_time_based_exit']:
            max_candles = self.exit_strategy['max_hold_candles']
            if candles_held >= max_candles:
                result['should_exit'] = True
                result['exit_type'] = 'time_exit'
                result['exit_price'] = current_price
                result['exit_size'] = remaining_size
                result['reason'] = f'Max hold time reached: {candles_held} >= {max_candles} candles'
                return result

        return result

    def _check_compression_increase(self, candle: pd.Series) -> bool:
        """
        Check if ribbon compression is INCREASING (ribbons tightening)

        KEY INSIGHT:
        - When ribbons SPREAD = big move happening (STAY IN!)
        - When ribbons COMPRESS = move exhausting (EXIT!)

        We entered on compression → expansion breakout.
        Now exit when compression starts increasing again = move done.

        UPDATED: Made LESS aggressive to let winners run!
        - Increased compression threshold from 70 → 85
        - Expansion must be strongly negative (< -3, not -2)

        Returns:
            True if compression increasing (exit signal)
        """
        # Need compression_score and expansion_rate
        compression = candle.get('compression_score', 0)
        expansion = candle.get('expansion_rate', 0)

        if compression == 0:
            return False

        # Exit ONLY if:
        # 1. Compression is VERY HIGH (score > 85) - ribbons are VERY tight now
        # 2. Expansion is STRONGLY negative (< -3) - ribbons rapidly tightening
        # This ensures we stay in the big moves and only exit when move clearly exhausted
        if compression > 85 and expansion < -3:
            return True

        return False

    def _check_yellow_ema_break(self, candle: pd.Series, direction: str, entry_price: float) -> str:
        """
        Check if price broke below/above yellow EMA (20 or 21)

        Yellow EMA acts as dynamic support/resistance in ribbon strategy.

        For LONG: Exit if price < yellow EMA (support broken)
        For SHORT: Exit if price > yellow EMA (resistance broken)

        UPDATED: Made LESS aggressive to let winners run!
        - Allow 2% buffer below/above yellow EMA before exiting
        - This prevents premature exits on small pullbacks during big moves

        Returns:
            Reason string if break detected, empty string otherwise
        """
        price = candle['close']
        ema20 = candle.get('MMA20_value', 0)
        ema21 = candle.get('MMA21_value', 0)

        # Use whichever yellow EMA is available
        yellow_ema = ema20 if ema20 > 0 else ema21
        if yellow_ema == 0:
            return ""

        if direction == 'long':
            # For longs, exit ONLY if price crosses 2% below yellow EMA (significant break)
            # This allows for small pullbacks without exiting the big move
            if price < yellow_ema * 0.98:
                return f'Price broke significantly below yellow EMA: {price:.2f} < {yellow_ema * 0.98:.2f}'

        elif direction == 'short':
            # For shorts, exit ONLY if price crosses 2% above yellow EMA
            if price > yellow_ema * 1.02:
                return f'Price broke significantly above yellow EMA: {price:.2f} > {yellow_ema * 1.02:.2f}'

        return ""

    def _check_stochastic_reversal(self, candle: pd.Series, direction: str, profit_pct: float) -> str:
        """
        Check for Stochastic Oscillator reversal signal (NEW EXIT)

        Professional day trading exit: Exit when momentum reverses in extreme zones

        For LONG:
        - Exit if Stochastic is overbought (>80) AND %K crosses below %D (bearish crossover)
        - This indicates momentum is weakening at the top

        For SHORT:
        - Exit if Stochastic is oversold (<20) AND %K crosses above %D (bullish crossover)
        - This indicates momentum is weakening at the bottom

        Only applies when in profit to lock in gains at reversal points

        Args:
            candle: Current candle data
            direction: Trade direction
            profit_pct: Current profit percentage

        Returns:
            Reason string if reversal detected, empty string otherwise
        """
        # Only check if we have Stochastic data and are in profit
        min_profit = self.exit_strategy.get('stochastic_exit_min_profit', 0.3)
        if profit_pct <= min_profit:
            return ""

        stoch_k = candle.get('stoch_k', None)
        stoch_d = candle.get('stoch_d', None)
        stoch_crossover = candle.get('stoch_crossover', 'none')

        if stoch_k is None or stoch_d is None:
            return ""

        if direction == 'long':
            # Exit LONG if overbought AND bearish crossover
            if stoch_k > 80 and stoch_crossover == 'bearish':
                return f'Stochastic reversal: Overbought ({stoch_k:.1f}) + bearish crossover (profit: {profit_pct:.2f}%)'
            # Also exit if severely overbought (>90) even without crossover
            elif stoch_k > 90:
                return f'Stochastic extreme overbought: {stoch_k:.1f} (profit: {profit_pct:.2f}%)'

        elif direction == 'short':
            # Exit SHORT if oversold AND bullish crossover
            if stoch_k < 20 and stoch_crossover == 'bullish':
                return f'Stochastic reversal: Oversold ({stoch_k:.1f}) + bullish crossover (profit: {profit_pct:.2f}%)'
            # Also exit if severely oversold (<10) even without crossover
            elif stoch_k < 10:
                return f'Stochastic extreme oversold: {stoch_k:.1f} (profit: {profit_pct:.2f}%)'

        return ""

    def _check_bollinger_reversal(self, candle: pd.Series, direction: str, profit_pct: float) -> str:
        """
        Check for Bollinger Band reversal signal (NEW EXIT)

        Professional day trading exit: Exit when price reaches opposite extreme

        For LONG:
        - Exit if price touches or exceeds upper Bollinger Band (overbought territory)
        - This indicates the move may be overextended

        For SHORT:
        - Exit if price touches or exceeds lower Bollinger Band (oversold territory)
        - This indicates the move may be overextended

        Only applies when in profit to lock in gains at band extremes

        Args:
            candle: Current candle data
            direction: Trade direction
            profit_pct: Current profit percentage

        Returns:
            Reason string if reversal detected, empty string otherwise
        """
        # Only check if we have Bollinger data and are in profit
        min_profit = self.exit_strategy.get('bollinger_exit_min_profit', 0.5)
        if profit_pct <= min_profit:
            return ""

        bb_position = candle.get('bb_position', 'middle')
        bb_upper = candle.get('bb_upper', None)
        bb_lower = candle.get('bb_lower', None)
        bb_width = candle.get('bb_width', 0)
        price = candle['close']

        if bb_upper is None or bb_lower is None:
            return ""

        if direction == 'long':
            # Exit LONG if price is at or above upper band (overbought)
            if bb_position == 'above' or (price >= bb_upper * 0.995):
                return f'Bollinger reversal: Price at upper band {price:.2f} >= {bb_upper:.2f} (profit: {profit_pct:.2f}%)'
            # Also consider exit if price is at upper position during band contraction
            elif bb_position == 'upper' and bb_width < 3.0:
                return f'Bollinger reversal: Upper band during contraction (profit: {profit_pct:.2f}%)'

        elif direction == 'short':
            # Exit SHORT if price is at or below lower band (oversold)
            if bb_position == 'below' or (price <= bb_lower * 1.005):
                return f'Bollinger reversal: Price at lower band {price:.2f} <= {bb_lower:.2f} (profit: {profit_pct:.2f}%)'
            # Also consider exit if price is at lower position during band contraction
            elif bb_position == 'lower' and bb_width < 3.0:
                return f'Bollinger reversal: Lower band during contraction (profit: {profit_pct:.2f}%)'

        return ""

    def _check_vwap_cross(self, candle: pd.Series, direction: str, profit_pct: float) -> str:
        """
        Check for VWAP cross signal (NEW EXIT)

        Professional day trading exit: Exit when price crosses back through VWAP

        For LONG:
        - Exit if price crosses below VWAP (losing institutional support)
        - This indicates buyers are weakening and sellers taking control

        For SHORT:
        - Exit if price crosses above VWAP (losing institutional resistance)
        - This indicates sellers are weakening and buyers taking control

        Only applies when in profit to protect gains when institutional flow reverses

        Args:
            candle: Current candle data
            direction: Trade direction
            profit_pct: Current profit percentage

        Returns:
            Reason string if cross detected, empty string otherwise
        """
        # Only check if we have VWAP data and are in profit
        min_profit = self.exit_strategy.get('vwap_exit_min_profit', 0.5)
        if profit_pct <= min_profit:
            return ""

        vwap = candle.get('vwap', None)
        vwap_position = candle.get('vwap_position', 'at_vwap')
        price = candle['close']

        if vwap is None:
            return ""

        if direction == 'long':
            # Exit LONG if price crosses below VWAP (institutional support lost)
            if vwap_position in ['below', 'strong_below'] or price < vwap * 0.998:
                distance_pct = (vwap - price) / vwap * 100
                return f'VWAP cross: Price below VWAP {price:.2f} < {vwap:.2f} (-{distance_pct:.2f}%, profit: {profit_pct:.2f}%)'

        elif direction == 'short':
            # Exit SHORT if price crosses above VWAP (institutional resistance lost)
            if vwap_position in ['above', 'strong_above'] or price > vwap * 1.002:
                distance_pct = (price - vwap) / vwap * 100
                return f'VWAP cross: Price above VWAP {price:.2f} > {vwap:.2f} (+{distance_pct:.2f}%, profit: {profit_pct:.2f}%)'

        return ""

    def simulate_trade_outcome(self, entry_candle_idx: int, df: pd.DataFrame, entry_signal: Dict) -> Dict:
        """
        Simulate full trade lifecycle from entry to complete exit

        Args:
            entry_candle_idx: Index of entry candle
            df: Full DataFrame with all candles
            entry_signal: Entry signal dict from EntryDetector

        Returns:
            dict with complete trade results:
                - entry_price, entry_time, direction
                - exits: list of partial exits with prices, sizes, times
                - final_exit_price, final_exit_time, final_exit_type
                - total_profit_pct, total_profit_usd
                - max_favorable_excursion (MFE)
                - max_adverse_excursion (MAE)
                - candles_held, duration
        """
        # Initialize trade
        entry_candle = df.iloc[entry_candle_idx]
        trade = {
            'entry_price': entry_candle['close'],
            'entry_time': entry_candle['timestamp'],
            'direction': entry_signal['direction'],
            'remaining_size': 100,
            'exits_taken': [],
            'exit_levels': None
        }

        # Calculate exit levels
        df_at_entry = df.iloc[:entry_candle_idx+1]
        trade['exit_levels'] = self.calculate_exit_levels(
            trade['entry_price'],
            trade['direction'],
            df_at_entry
        )

        partial_exits = []
        mfe = 0  # Maximum Favorable Excursion
        mae = 0  # Maximum Adverse Excursion

        # Simulate forward from entry
        for i in range(entry_candle_idx + 1, len(df)):
            current_candle = df.iloc[i]
            candles_held = i - entry_candle_idx

            # Update MFE and MAE
            if trade['direction'] == 'long':
                profit = (current_candle['high'] - trade['entry_price']) / trade['entry_price'] * 100
                loss = (current_candle['low'] - trade['entry_price']) / trade['entry_price'] * 100
            else:
                profit = (trade['entry_price'] - current_candle['low']) / trade['entry_price'] * 100
                loss = (trade['entry_price'] - current_candle['high']) / trade['entry_price'] * 100

            mfe = max(mfe, profit)
            mae = min(mae, loss)

            # Check for exit
            exit_check = self.check_exit(trade, current_candle, candles_held)

            if exit_check['should_exit']:
                # Record partial exit
                partial_exit = {
                    'exit_type': exit_check['exit_type'],
                    'exit_price': exit_check['exit_price'],
                    'exit_time': current_candle['timestamp'],
                    'exit_size': exit_check['exit_size'],
                    'profit_pct': exit_check['profit_pct'],
                    'candle_idx': i,
                    'candles_held': candles_held
                }
                partial_exits.append(partial_exit)

                # Update trade state
                trade['remaining_size'] -= exit_check['exit_size']
                trade['exits_taken'].append(exit_check['exit_type'])

                # If fully exited, we're done
                if trade['remaining_size'] <= 0:
                    break

        # Calculate total profit (weighted average of all exits)
        total_profit_pct = sum(exit['profit_pct'] * exit['exit_size'] / 100 for exit in partial_exits)

        # Compile results
        result = {
            'entry_price': trade['entry_price'],
            'entry_time': trade['entry_time'],
            'entry_idx': entry_candle_idx,
            'direction': trade['direction'],
            'exit_levels': trade['exit_levels'],
            'exits': partial_exits,
            'num_exits': len(partial_exits),
            'final_exit_type': partial_exits[-1]['exit_type'] if partial_exits else None,
            'final_exit_price': partial_exits[-1]['exit_price'] if partial_exits else None,
            'final_exit_time': partial_exits[-1]['exit_time'] if partial_exits else None,
            'total_profit_pct': total_profit_pct,
            'mfe': mfe,
            'mae': mae,
            'candles_held': partial_exits[-1]['candles_held'] if partial_exits else 0,
        }

        return result


if __name__ == '__main__':
    """Test exit manager"""
    print("Exit Manager - Test simulation")

    # Create sample trade
    trade = {
        'entry_price': 3000.0,
        'direction': 'long',
        'remaining_size': 100,
        'exits_taken': []
    }

    # Create exit manager
    manager = ExitManager()

    # Calculate exit levels
    exit_levels = manager.calculate_exit_levels(3000.0, 'long')
    print("\n📊 Exit Levels for LONG @ 3000:")
    print(f"   Stop Loss: {exit_levels['stop_loss']:.2f}")
    print(f"   TP1 (+1%): {exit_levels['take_profit_1']:.2f} - Exit {exit_levels['tp_sizes'][0]}%")
    print(f"   TP2 (+2%): {exit_levels['take_profit_2']:.2f} - Exit {exit_levels['tp_sizes'][1]}%")
    print(f"   TP3 (+3%): {exit_levels['take_profit_3']:.2f} - Exit {exit_levels['tp_sizes'][2]}%")

    print("\n✅ Exit Manager ready for backtesting!")
