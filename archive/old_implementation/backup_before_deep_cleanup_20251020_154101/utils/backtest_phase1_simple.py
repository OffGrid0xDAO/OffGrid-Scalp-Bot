"""
Backtest Phase 1 Trading Rules - Simplified Version
Works with existing ribbon_state column from CSV
"""

import pandas as pd
import json
from datetime import datetime, timedelta


class Phase1BacktestSimple:
    """Simplified Phase 1 backtest using existing ribbon states"""

    def __init__(self):
        self.trades = []
        self.ema_data_path = 'trading_data/ema_data_5min.csv'

        # Load Phase 1 rules
        with open('trading_rules_phase1.json', 'r') as f:
            self.rules = json.load(f)

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

    def map_ribbon_state_to_tier(self, ribbon_state: str) -> tuple:
        """
        Map ribbon state to entry tier
        Returns: (tier, direction) or (None, None)
        """
        state = ribbon_state.lower()

        # Tier 1: all_green or all_red
        if state == 'all_green':
            return 1, 'LONG'
        elif state == 'all_red':
            return 1, 'SHORT'

        # Tier 2: mixed_green or mixed_red
        elif state in ['mixed_green', 'strong_green']:
            return 2, 'LONG'
        elif state in ['mixed_red', 'strong_red']:
            return 2, 'SHORT'

        # No entry
        return None, None

    def run_backtest(self, hours_back: int = 24):
        """Run Phase 1 backtest"""

        print(f"\n{'='*70}")
        print(f"🧪 PHASE 1 BACKTEST (SIMPLIFIED) - Last {hours_back} Hours")
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
            current_price = current.get('price', current.get('close', 0))
            current_state = current.get('ribbon_state', 'mixed').lower()

            # Track ribbon transitions
            if current_state != last_state:
                ribbon_transition_time = current_time
                last_state = current_state

            # Check stability (how long in current state)
            stability_minutes = 0
            if ribbon_transition_time:
                stability_minutes = (current_time - ribbon_transition_time).total_seconds() / 60

            # Check for entry if not in position
            if not in_position:
                tier, direction = self.map_ribbon_state_to_tier(current_state)

                if tier is not None:
                    # Get tier config
                    tier_configs = {
                        1: self.rules['entry_rules']['entry_tiers']['tier_1_strong_trend'],
                        2: self.rules['entry_rules']['entry_tiers']['tier_2_moderate_trend']
                    }
                    tier_config = tier_configs.get(tier)

                    # Check stability requirement
                    if stability_minutes >= tier_config['min_ribbon_stability_minutes']:
                        in_position = True
                        entry_idx = idx
                        entry_direction = direction
                        entry_price = current_price
                        entry_time = current_time
                        entry_tier = tier

                        print(f"\n📈 ENTRY T{tier}: {direction} @ ${current_price:.2f}")
                        print(f"   Time: {current_time}")
                        print(f"   State: {current_state} ({stability_minutes:.1f}min stable)")

            # Check for exit if in position
            else:
                # Get tier-specific exit rules
                tier_keys = {
                    1: 'tier_1_strong_trend',
                    2: 'tier_2_moderate_trend'
                }
                tier_key = tier_keys.get(entry_tier, 'tier_2_moderate_trend')
                exit_rules = self.rules['exit_rules'][tier_key]

                # Calculate P&L
                if entry_direction == 'LONG':
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - current_price) / entry_price * 100

                # Hold time
                hold_time = (current_time - entry_time).total_seconds() / 60

                should_exit = False
                exit_reason = None

                # CHECK 1: Min hold time
                if hold_time < exit_rules['min_hold_minutes']:
                    continue  # Keep holding

                # CHECK 2: Profit target
                if pnl_pct >= exit_rules['profit_target_pct'] * 100:
                    should_exit = True
                    exit_reason = 'profit_target'

                # CHECK 3: Stop loss
                elif pnl_pct <= -exit_rules['stop_loss_pct'] * 100:
                    should_exit = True
                    exit_reason = 'stop_loss'

                # CHECK 4: Ribbon reversal (tier-specific)
                elif entry_tier == 1:
                    # Tier 1: Only exit on OPPOSITE strong state
                    if entry_direction == 'LONG' and current_state == 'all_red':
                        should_exit = True
                        exit_reason = 'strong_reversal'
                    elif entry_direction == 'SHORT' and current_state == 'all_green':
                        should_exit = True
                        exit_reason = 'strong_reversal'

                elif entry_tier == 2:
                    # Tier 2: Exit on any opposite state
                    if entry_direction == 'LONG' and 'red' in current_state:
                        should_exit = True
                        exit_reason = 'ribbon_reversal'
                    elif entry_direction == 'SHORT' and 'green' in current_state:
                        should_exit = True
                        exit_reason = 'ribbon_reversal'

                # Execute exit
                if should_exit:
                    trade = {
                        'entry_time': entry_time.isoformat(),
                        'exit_time': current_time.isoformat(),
                        'direction': entry_direction,
                        'entry_tier': int(entry_tier),
                        'entry_price': float(entry_price),
                        'exit_price': float(current_price),
                        'pnl_pct': float(pnl_pct),
                        'hold_time_minutes': float(hold_time),
                        'exit_reason': exit_reason,
                        'winner': int(pnl_pct > 0)
                    }

                    self.trades.append(trade)

                    print(f"\n📉 EXIT T{entry_tier}: {exit_reason}")
                    print(f"   Exit: ${current_price:.2f}")
                    print(f"   PnL: {pnl_pct:+.2f}%")
                    print(f"   Hold: {hold_time:.1f} minutes")

                    # Reset
                    in_position = False

        # Save results
        self.save_results()

        # Print summary
        self.print_summary()

    def save_results(self):
        """Save backtest results to JSON"""
        result = {
            'backtest_type': 'phase1_simplified',
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
        if summary['tier_1_trades'] > 0:
            print(f"    Avg Hold: {summary['tier_1_avg_hold']:.1f} min")
            print(f"    Avg PnL: {summary['tier_1_avg_pnl']:+.2f}%")

        print(f"  Tier 2 (Moderate Trend):")
        print(f"    Trades: {summary['tier_2_trades']}")
        if summary['tier_2_trades'] > 0:
            print(f"    Avg Hold: {summary['tier_2_avg_hold']:.1f} min")
            print(f"    Avg PnL: {summary['tier_2_avg_pnl']:+.2f}%")

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
    backtest = Phase1BacktestSimple()
    backtest.run_backtest(hours_back=24)
