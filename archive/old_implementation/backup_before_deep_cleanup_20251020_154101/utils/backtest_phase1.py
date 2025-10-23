"""
Backtest Phase 1 Trading Rules
Tests the enhanced tiered entry/exit system
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from rule_based_trader_phase1 import RuleBasedTraderPhase1


class Phase1Backtest:
    """Backtest Phase 1 rules with tiered entries"""

    def __init__(self):
        self.trader = RuleBasedTraderPhase1()
        self.trades = []
        self.ema_data_path = 'trading_data/ema_data_5min.csv'

    def load_data(self, hours_back: int = 24) -> pd.DataFrame:
        """Load EMA data for backtest"""
        try:
            df = pd.read_csv(self.ema_data_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Filter to recent
            cutoff = datetime.now() - timedelta(hours=hours_back)
            df = df[df['timestamp'] >= cutoff]

            # Sort by time
            df = df.sort_values('timestamp').reset_index(drop=True)

            print(f"✅ Loaded {len(df)} candles ({hours_back} hours)")
            return df

        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return pd.DataFrame()

    def prepare_indicators(self, row: pd.Series) -> dict:
        """Convert row to indicators format"""
        indicators = {}

        for ema in [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120]:
            if f'ema_{ema}_color' in row and f'ema_{ema}_color_intensity' in row:
                indicators[f'MMA{ema}'] = {
                    'color': row[f'ema_{ema}_color'],
                    'intensity': row[f'ema_{ema}_color_intensity'],
                    'value': row.get(f'ema_{ema}', 0)
                }

        return indicators

    def run_backtest(self, hours_back: int = 24):
        """Run Phase 1 backtest"""

        print(f"\n{'='*70}")
        print(f"🧪 PHASE 1 BACKTEST - Last {hours_back} Hours")
        print(f"{'='*70}\n")

        df = self.load_data(hours_back)

        if df.empty:
            print("❌ No data to backtest")
            return

        # State tracking
        in_position = False
        entry_idx = None
        entry_direction = None
        entry_price = None
        entry_time = None
        entry_tier = None
        ribbon_transition_time = None
        last_state = None

        for idx in range(len(df)):
            current = df.iloc[idx]
            current_time = current['timestamp']
            current_price = current.get('close', 0)

            # Prepare indicators
            indicators = self.prepare_indicators(current)

            # Track ribbon transitions
            pattern = self.trader.extract_ema_pattern(indicators)
            current_state = self.trader.determine_ribbon_state(pattern)

            if current_state != last_state:
                ribbon_transition_time = current_time
                last_state = current_state

            # Check for entry if not in position
            if not in_position:
                should_enter, direction, confidence, reasoning, tier = self.trader.check_entry_signal(
                    indicators_5min=indicators,
                    indicators_15min=indicators,  # Using 5min for both (simplified)
                    current_price=current_price,
                    ribbon_transition_time=ribbon_transition_time
                )

                if should_enter:
                    in_position = True
                    entry_idx = idx
                    entry_direction = direction
                    entry_price = current_price
                    entry_time = current_time
                    entry_tier = tier

                    print(f"\n📈 ENTRY {tier}: {direction} @ ${current_price:.2f}")
                    print(f"   Time: {current_time}")
                    print(f"   {reasoning}")

            # Check for exit if in position
            else:
                should_exit, exit_reason, reasoning = self.trader.check_exit_signal(
                    indicators_5min=indicators,
                    indicators_15min=indicators,
                    entry_direction=entry_direction,
                    entry_price=entry_price,
                    current_price=current_price,
                    entry_time=entry_time,
                    entry_tier=entry_tier
                )

                if should_exit:
                    exit_price = current_price
                    exit_time = current_time
                    hold_time = (exit_time - entry_time).total_seconds() / 60

                    # Calculate PnL
                    if entry_direction == 'LONG':
                        pnl_pct = (exit_price - entry_price) / entry_price * 100
                    else:
                        pnl_pct = (entry_price - exit_price) / entry_price * 100

                    trade = {
                        'entry_time': entry_time.isoformat(),
                        'exit_time': exit_time.isoformat(),
                        'direction': entry_direction,
                        'entry_tier': entry_tier,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct,
                        'hold_time_minutes': hold_time,
                        'exit_reason': exit_reason,
                        'winner': pnl_pct > 0
                    }

                    self.trades.append(trade)

                    print(f"\n📉 EXIT {entry_tier}: {exit_reason}")
                    print(f"   Exit: ${exit_price:.2f}")
                    print(f"   PnL: {pnl_pct:+.2f}%")
                    print(f"   Hold: {hold_time:.1f} minutes")

                    # Reset
                    in_position = False
                    entry_idx = None

        # Save results
        self.save_results()

        # Print summary
        self.print_summary()

    def save_results(self):
        """Save backtest results to JSON"""
        result = {
            'backtest_type': 'phase1_enhanced',
            'timestamp': datetime.now().isoformat(),
            'total_trades': len(self.trades),
            'trades': self.trades,
            'summary': self.calculate_summary()
        }

        with open('trading_data/backtest_phase1_results.json', 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n💾 Results saved to: trading_data/backtest_phase1_results.json")

    def calculate_summary(self) -> dict:
        """Calculate summary statistics"""

        if not self.trades:
            return {}

        winners = [t for t in self.trades if t['winner']]
        losers = [t for t in self.trades if not t['winner']]

        # By tier
        tier_1_trades = [t for t in self.trades if t['entry_tier'] == 1]
        tier_2_trades = [t for t in self.trades if t['entry_tier'] == 2]
        tier_3_trades = [t for t in self.trades if t['entry_tier'] == 3]

        summary = {
            'total_trades': len(self.trades),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': len(winners) / len(self.trades) if self.trades else 0,
            'total_pnl': sum(t['pnl_pct'] for t in self.trades),
            'avg_pnl': sum(t['pnl_pct'] for t in self.trades) / len(self.trades),
            'avg_winner': sum(t['pnl_pct'] for t in winners) / len(winners) if winners else 0,
            'avg_loser': sum(t['pnl_pct'] for t in losers) / len(losers) if losers else 0,
            'avg_hold_time': sum(t['hold_time_minutes'] for t in self.trades) / len(self.trades),

            # By tier
            'tier_1_trades': len(tier_1_trades),
            'tier_1_avg_hold': sum(t['hold_time_minutes'] for t in tier_1_trades) / len(tier_1_trades) if tier_1_trades else 0,
            'tier_1_avg_pnl': sum(t['pnl_pct'] for t in tier_1_trades) / len(tier_1_trades) if tier_1_trades else 0,

            'tier_2_trades': len(tier_2_trades),
            'tier_2_avg_hold': sum(t['hold_time_minutes'] for t in tier_2_trades) / len(tier_2_trades) if tier_2_trades else 0,
            'tier_2_avg_pnl': sum(t['pnl_pct'] for t in tier_2_trades) / len(tier_2_trades) if tier_2_trades else 0,

            'tier_3_trades': len(tier_3_trades),
            'tier_3_avg_hold': sum(t['hold_time_minutes'] for t in tier_3_trades) / len(tier_3_trades) if tier_3_trades else 0,
            'tier_3_avg_pnl': sum(t['pnl_pct'] for t in tier_3_trades) / len(tier_3_trades) if tier_3_trades else 0,

            # Exit reasons
            'profit_targets_hit': len([t for t in self.trades if t['exit_reason'] == 'profit_target']),
            'stop_losses_hit': len([t for t in self.trades if t['exit_reason'] == 'stop_loss']),
            'ribbon_reversals': len([t for t in self.trades if 'reversal' in t['exit_reason']]),
        }

        return summary

    def print_summary(self):
        """Print formatted summary"""

        if not self.trades:
            print("\n❌ No trades executed in backtest")
            return

        summary = self.calculate_summary()

        print(f"\n{'='*70}")
        print("📊 PHASE 1 BACKTEST RESULTS")
        print(f"{'='*70}\n")

        print(f"Overall Performance:")
        print(f"  Total Trades: {summary['total_trades']}")
        print(f"  Winners: {summary['winners']} ({summary['win_rate']*100:.1f}%)")
        print(f"  Losers: {summary['losers']}")
        print(f"  Total PnL: {summary['total_pnl']:+.2f}%")
        print(f"  Avg PnL per Trade: {summary['avg_pnl']:+.2f}%")
        print(f"  Avg Winner: +{summary['avg_winner']:.2f}%")
        print(f"  Avg Loser: {summary['avg_loser']:.2f}%")
        print(f"  Avg Hold Time: {summary['avg_hold_time']:.1f} minutes")

        print(f"\nBy Entry Tier:")
        print(f"  Tier 1 (Strong Trend):")
        print(f"    Trades: {summary['tier_1_trades']}")
        print(f"    Avg Hold: {summary['tier_1_avg_hold']:.1f} min")
        print(f"    Avg PnL: {summary['tier_1_avg_pnl']:+.2f}%")

        print(f"  Tier 2 (Moderate Trend):")
        print(f"    Trades: {summary['tier_2_trades']}")
        print(f"    Avg Hold: {summary['tier_2_avg_hold']:.1f} min")
        print(f"    Avg PnL: {summary['tier_2_avg_pnl']:+.2f}%")

        if summary['tier_3_trades'] > 0:
            print(f"  Tier 3 (Quick Scalp):")
            print(f"    Trades: {summary['tier_3_trades']}")
            print(f"    Avg Hold: {summary['tier_3_avg_hold']:.1f} min")
            print(f"    Avg PnL: {summary['tier_3_avg_pnl']:+.2f}%")

        print(f"\nExit Breakdown:")
        print(f"  Profit Targets: {summary['profit_targets_hit']}")
        print(f"  Stop Losses: {summary['stop_losses_hit']}")
        print(f"  Ribbon Reversals: {summary['ribbon_reversals']}")

        print(f"\n{'='*70}")

        # Compare with original backtest
        print(f"\n📈 IMPROVEMENT vs ORIGINAL:")
        print(f"  Hold Time: 3.5min → {summary['avg_hold_time']:.1f}min ({summary['avg_hold_time']/3.5:.1f}x improvement)")
        print(f"  PnL: -0.14% → {summary['total_pnl']:+.2f}% ({summary['total_pnl']+0.14:+.2f}% improvement)")
        print(f"  Win Rate: 37% → {summary['win_rate']*100:.1f}% ({summary['win_rate']*100-37:+.1f}% improvement)")

        print(f"\n{'='*70}\n")


if __name__ == '__main__':
    backtest = Phase1Backtest()
    backtest.run_backtest(hours_back=24)
