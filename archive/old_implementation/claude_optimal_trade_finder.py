"""
Claude-Powered Optimal Trade Finder
Uses Claude AI to analyze historical EMA patterns and identify best trade opportunities
Much smarter than pure mathematical rules
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path
from anthropic import Anthropic
import os


class ClaudeOptimalTradeFinder:
    """
    Use Claude AI to find optimal trades by analyzing EMA patterns
    Claude can see patterns and opportunities that mathematical rules miss
    """

    def __init__(self,
                 ema_5min_file='trading_data/ema_data_5min.csv',
                 api_key=None):

        self.ema_5min_file = ema_5min_file
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')

        if not self.api_key or self.api_key == 'your_anthropic_api_key_here':
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        self.client = Anthropic(api_key=self.api_key)
        self.trades = []
        self.total_api_cost = 0.0

    def load_data(self, hours_back: int = 24) -> pd.DataFrame:
        """Load EMA data for analysis"""

        if not Path(self.ema_5min_file).exists():
            print(f"⚠️  EMA data file not found: {self.ema_5min_file}")
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.ema_5min_file, on_bad_lines='skip')

            if df.empty:
                return df

            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.dropna(subset=['timestamp'])

            # Filter to recent
            cutoff = datetime.now() - timedelta(hours=hours_back)
            df = df[df['timestamp'] >= cutoff]

            # Sort by time
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"⚠️  Error loading EMA data: {e}")
            return pd.DataFrame()

    def prepare_data_for_claude(self, df: pd.DataFrame, window_size: int = 120) -> List[Dict]:
        """
        Break data into windows for Claude to analyze
        Each window = 2 hours of 5min candles (24 candles per window)
        """

        windows = []

        # Process in chunks to avoid overwhelming Claude
        for i in range(0, len(df), window_size):
            window_df = df.iloc[i:i+window_size]

            if len(window_df) < 12:  # Need at least 1 hour of data
                continue

            # Extract key info for each candle
            candles = []
            for idx, row in window_df.iterrows():
                candle = {
                    'time': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'price': row.get('close', row.get('price', 0)),
                    'high': row.get('high', row.get('price', 0)),
                    'low': row.get('low', row.get('price', 0)),
                    'ribbon_state': row.get('ribbon_state', 'unknown'),
                }

                # Count light EMAs
                light_green = 0
                light_red = 0
                for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60]:
                    color_col = f'MMA{ema}_color'
                    intensity_col = f'MMA{ema}_intensity'

                    if color_col in row and intensity_col in row:
                        if row[color_col] == 'green' and row[intensity_col] == 'light':
                            light_green += 1
                        elif row[color_col] == 'red' and row[intensity_col] == 'light':
                            light_red += 1

                candle['light_green_emas'] = light_green
                candle['light_red_emas'] = light_red

                candles.append(candle)

            windows.append({
                'start_time': candles[0]['time'],
                'end_time': candles[-1]['time'],
                'candles': candles
            })

        return windows

    def ask_claude_for_trades(self, window: Dict) -> List[Dict]:
        """
        Ask Claude to analyze a window and find optimal trade opportunities
        """

        candles_summary = []
        for i, c in enumerate(window['candles']):
            candles_summary.append(
                f"{i}: {c['time']} | ${c['price']:.2f} | {c['ribbon_state']} | "
                f"💚{c['light_green_emas']} ❤️{c['light_red_emas']}"
            )

        prompt = f"""You are an expert trading analyst analyzing EMA ribbon patterns for scalping opportunities.

I have 5-minute candle data with EMA ribbon states. Your job is to find the BEST trade opportunities using PERFECT HINDSIGHT.

## DATA (5min candles):
{chr(10).join(candles_summary[:50])}  # Limit to 50 candles to avoid token limit

## YOUR TASK:

Analyze this data and identify the OPTIMAL trades you would have taken with perfect hindsight.

For each trade opportunity, consider:
1. **Entry**: When ribbon shows strong alignment (all_green/all_red with many light EMAs)
2. **Exit**: When price has moved enough OR ribbon flips OR momentum fades
3. **Hold time**: How long to ride the trend (balance profit vs risk)
4. **Quality**: Only high-probability setups with clear trends

## OUTPUT FORMAT:

Respond with a JSON array of trades:

```json
[
  {{
    "entry_idx": 5,
    "exit_idx": 15,
    "direction": "LONG",
    "entry_reason": "Ribbon flipped to all_green with 8 light green EMAs - strong bullish setup",
    "exit_reason": "Price gained 1.2%, ribbon starting to weaken - take profit",
    "confidence": 0.9,
    "expected_pnl_pct": 1.2
  }},
  ...
]
```

Rules:
- Only include trades you're HIGHLY confident would have been profitable
- Be selective - quality over quantity
- Consider realistic profit targets (0.5-2%)
- Avoid choppy/unclear setups
- Max 5 trades per response

Analyze and find the best opportunities:
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "[" in response_text and "]" in response_text:
                json_start = response_text.find("[")
                json_end = response_text.rfind("]") + 1
                json_str = response_text[json_start:json_end]
            else:
                print(f"  ⚠️  Could not parse Claude response")
                return []

            trades = json.loads(json_str)

            # Calculate cost
            usage = response.usage
            input_cost = (usage.input_tokens / 1_000_000) * 3.0
            output_cost = (usage.output_tokens / 1_000_000) * 15.0
            self.total_api_cost += input_cost + output_cost

            # Convert to our format with actual prices
            validated_trades = []
            for trade in trades:
                entry_idx = trade['entry_idx']
                exit_idx = trade['exit_idx']

                if entry_idx >= len(window['candles']) or exit_idx >= len(window['candles']):
                    continue

                entry_candle = window['candles'][entry_idx]
                exit_candle = window['candles'][exit_idx]

                entry_price = entry_candle['price']
                exit_price = exit_candle['price']

                # Calculate actual PnL
                if trade['direction'] == 'LONG':
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100

                # Only keep if actually profitable
                if pnl_pct > 0:
                    validated_trades.append({
                        'entry_time': entry_candle['time'],
                        'exit_time': exit_candle['time'],
                        'direction': trade['direction'],
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'entry_reason': trade.get('entry_reason', ''),
                        'exit_reason': trade.get('exit_reason', ''),
                        'confidence': trade.get('confidence', 0.8),
                        'pnl_pct': pnl_pct,
                        'winner': True
                    })

            return validated_trades

        except Exception as e:
            print(f"  ⚠️  Claude analysis failed: {e}")
            return []

    def find_optimal_trades(self, hours_back: int = 24) -> Dict:
        """
        Main function: Use Claude to find optimal trades
        """

        print(f"\n🤖 CLAUDE-POWERED OPTIMAL TRADE FINDER")
        print("="*70)
        print(f"Analyzing last {hours_back} hours with AI...")

        df = self.load_data(hours_back)

        if df.empty:
            return {
                'status': 'no_data',
                'trades': [],
                'summary': {},
                'api_cost': 0.0
            }

        print(f"  📊 Loaded {len(df)} candles")

        # Prepare windows
        windows = self.prepare_data_for_claude(df, window_size=120)
        print(f"  🪟 Split into {len(windows)} windows")

        # Analyze each window with Claude
        all_trades = []
        for i, window in enumerate(windows, 1):
            print(f"\n  [{i}/{len(windows)}] Analyzing window {window['start_time']} to {window['end_time']}...")

            trades = self.ask_claude_for_trades(window)
            all_trades.extend(trades)

            print(f"    ✅ Found {len(trades)} optimal trades")

        self.trades = all_trades

        # Calculate summary
        summary = self._calculate_summary()

        print(f"\n{'='*70}")
        print(f"🎯 CLAUDE FOUND {len(all_trades)} OPTIMAL TRADES")
        print(f"   Total PnL: +{summary.get('total_pnl', 0):.2f}%")
        print(f"   Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
        print(f"   Avg Hold: {summary.get('avg_hold_time', 0):.1f} minutes")
        print(f"💰 API Cost: ${self.total_api_cost:.4f}")
        print(f"{'='*70}\n")

        return {
            'status': 'success',
            'method': 'claude_ai',
            'trades': self.trades,
            'summary': summary,
            'total_trades': len(self.trades),
            'total_pnl_pct': summary.get('total_pnl', 0),
            'api_cost': self.total_api_cost
        }

    def _calculate_summary(self) -> Dict:
        """Calculate summary statistics"""

        if not self.trades:
            return {
                'total_trades': 0,
                'winners': 0,
                'losers': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_winner': 0,
                'avg_loser': 0,
                'avg_hold_time': 0
            }

        winners = [t for t in self.trades if t.get('winner', t['pnl_pct'] > 0)]
        losers = [t for t in self.trades if not t.get('winner', t['pnl_pct'] > 0)]

        # Calculate hold times
        hold_times = []
        for t in self.trades:
            try:
                entry_dt = datetime.fromisoformat(t['entry_time'])
                exit_dt = datetime.fromisoformat(t['exit_time'])
                hold_minutes = (exit_dt - entry_dt).total_seconds() / 60
                hold_times.append(hold_minutes)
            except:
                hold_times.append(0)

        return {
            'total_trades': len(self.trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(self.trades) if self.trades else 0,
            'total_pnl': sum(t['pnl_pct'] for t in self.trades),
            'avg_winner': sum(t['pnl_pct'] for t in winners) / len(winners) if winners else 0,
            'avg_loser': sum(t['pnl_pct'] for t in losers) / len(losers) if losers else 0,
            'avg_hold_time': sum(hold_times) / len(hold_times) if hold_times else 0,
        }


if __name__ == '__main__':
    # Test the Claude-powered finder
    finder = ClaudeOptimalTradeFinder()
    results = finder.find_optimal_trades(hours_back=4)

    print("\n" + json.dumps(results, indent=2, default=str))
