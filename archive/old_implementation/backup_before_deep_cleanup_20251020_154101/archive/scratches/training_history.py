"""
Training History & Performance Tracking System
Stores each learning cycle with improvements, tips, and strategy evolution
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class TrainingHistory:
    """
    Tracks learning cycles, improvements, and strategy evolution
    Goal: Maximize profit while maintaining low risk (true scalper!)
    """

    def __init__(self, history_file='training_history.json'):
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load existing training history or create new"""
        if Path(self.history_file).exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        else:
            return {
                'started': datetime.now().isoformat(),
                'total_learning_cycles': 0,
                'learning_cycles': [],
                'strategy_evolution': [],
                'performance_summary': {
                    'highest_win_rate': 0,
                    'best_risk_reward_ratio': 0,
                    'most_profitable_setup': None,
                    'safest_setup': None
                }
            }

    def add_learning_cycle(self, analysis: Dict, insights: Dict):
        """
        Record a new learning cycle with detailed metrics

        Args:
            analysis: Backtest analysis results
            insights: Training insights generated
        """
        cycle_number = self.history['total_learning_cycles'] + 1
        timestamp = datetime.now().isoformat()

        # Extract key metrics
        winners = analysis.get('winners', [])
        losers = analysis.get('losers', [])
        win_rate = analysis.get('win_rate', 0)
        total_trades = analysis.get('total_trades', 0)

        # Calculate risk/reward metrics
        risk_reward = self._calculate_risk_reward(winners, losers)

        # Identify improvements from previous cycle
        improvements = self._identify_improvements(cycle_number)

        # Generate trading tips based on current data
        trading_tips = self._generate_trading_tips(analysis, insights)

        # Determine strategy adjustments
        strategy_changes = self._determine_strategy_changes(analysis, insights)

        # Create cycle record
        cycle = {
            'cycle_number': cycle_number,
            'timestamp': timestamp,
            'analysis_window': '4 hours',
            'metrics': {
                'total_opportunities': len(winners) + len(losers),
                'trades_simulated': total_trades,
                'win_rate': round(win_rate, 2),
                'winners': len(winners),
                'losers': len(losers),
                'best_hold_duration': analysis.get('best_hold_duration'),
                'avg_winner_pnl': round(sum(w['pnl_pct'] for w in winners) / len(winners), 3) if winners else 0,
                'avg_loser_pnl': round(sum(l['pnl_pct'] for l in losers) / len(losers), 3) if losers else 0,
                'risk_reward_ratio': round(risk_reward, 2),
                'profit_factor': self._calculate_profit_factor(winners, losers)
            },
            'improvements_from_previous': improvements,
            'trading_tips': trading_tips,
            'strategy_changes': strategy_changes,
            'winning_patterns': {
                'avg_30min_range': round(sum(w['range_30min'] for w in winners) / len(winners), 3) if winners else 0,
                'avg_price_location': round(sum(w['price_location_pct'] for w in winners) / len(winners), 1) if winners else 0,
                'avg_ribbon_flips': round(sum(w['ribbon_flips_30min'] for w in winners) / len(winners), 1) if winners else 0,
                'best_direction': self._get_best_direction(winners)
            },
            'losing_patterns': {
                'avg_30min_range': round(sum(l['range_30min'] for l in losers) / len(losers), 3) if losers else 0,
                'ranging_losses': len([l for l in losers if l['range_30min'] < 0.4]),
                'choppy_losses': len([l for l in losers if l['ribbon_flips_30min'] >= 3]),
                'worst_direction': self._get_worst_direction(losers)
            },
            'scalper_score': self._calculate_scalper_score(analysis)
        }

        # Add to history
        self.history['learning_cycles'].append(cycle)
        self.history['total_learning_cycles'] = cycle_number

        # Update strategy evolution
        if strategy_changes:
            self.history['strategy_evolution'].append({
                'cycle': cycle_number,
                'timestamp': timestamp,
                'changes': strategy_changes
            })

        # Update performance summary
        self._update_performance_summary(cycle)

        # Save to file
        self._save_history()

        return cycle

    def _calculate_risk_reward(self, winners: List, losers: List) -> float:
        """Calculate risk/reward ratio (avg win / avg loss)"""
        if not winners or not losers:
            return 0

        avg_win = sum(w['pnl_pct'] for w in winners) / len(winners)
        avg_loss = abs(sum(l['pnl_pct'] for l in losers) / len(losers))

        return avg_win / avg_loss if avg_loss > 0 else 0

    def _calculate_profit_factor(self, winners: List, losers: List) -> float:
        """Calculate profit factor (total wins / total losses)"""
        if not losers:
            return 999 if winners else 0

        total_wins = sum(w['pnl_pct'] for w in winners)
        total_losses = abs(sum(l['pnl_pct'] for l in losers))

        return round(total_wins / total_losses, 2) if total_losses > 0 else 999

    def _get_best_direction(self, winners: List) -> str:
        """Determine which direction has more winners"""
        if not winners:
            return "NONE"

        long_wins = len([w for w in winners if w['direction'] == 'LONG'])
        short_wins = len([w for w in winners if w['direction'] == 'SHORT'])

        if long_wins > short_wins:
            return f"LONG ({long_wins} wins)"
        elif short_wins > long_wins:
            return f"SHORT ({short_wins} wins)"
        else:
            return "EQUAL"

    def _get_worst_direction(self, losers: List) -> str:
        """Determine which direction has more losers"""
        if not losers:
            return "NONE"

        long_losses = len([l for l in losers if l['direction'] == 'LONG'])
        short_losses = len([l for l in losers if l['direction'] == 'SHORT'])

        if long_losses > short_losses:
            return f"LONG ({long_losses} losses)"
        elif short_losses > long_losses:
            return f"SHORT ({short_losses} losses)"
        else:
            return "EQUAL"

    def _calculate_scalper_score(self, analysis: Dict) -> Dict:
        """
        Calculate scalper effectiveness score (0-100)
        Goal: High win rate + Good R:R + Quick trades + Low drawdown
        """
        winners = analysis.get('winners', [])
        losers = analysis.get('losers', [])
        win_rate = analysis.get('win_rate', 0)

        # Scalper scoring components
        win_rate_score = min(win_rate * 2, 40)  # Max 40 points (20%+ win rate = full)

        # Quick execution score (prefer 10-20 min holds)
        best_hold = analysis.get('best_hold_duration', 30)
        if 10 <= best_hold <= 20:
            speed_score = 20
        elif 5 <= best_hold <= 25:
            speed_score = 15
        else:
            speed_score = 10

        # Risk management score
        risk_reward = self._calculate_risk_reward(winners, losers)
        if risk_reward >= 2:
            risk_score = 20
        elif risk_reward >= 1.5:
            risk_score = 15
        elif risk_reward >= 1:
            risk_score = 10
        else:
            risk_score = 5

        # Consistency score (avoiding big losses)
        if losers:
            max_loss = abs(min(l['pnl_pct'] for l in losers))
            if max_loss < 0.15:  # Max loss < 0.15%
                consistency_score = 20
            elif max_loss < 0.30:
                consistency_score = 15
            elif max_loss < 0.50:
                consistency_score = 10
            else:
                consistency_score = 5
        else:
            consistency_score = 20

        total_score = win_rate_score + speed_score + risk_score + consistency_score

        return {
            'total': round(total_score, 1),
            'win_rate_component': round(win_rate_score, 1),
            'speed_component': round(speed_score, 1),
            'risk_management_component': round(risk_score, 1),
            'consistency_component': round(consistency_score, 1),
            'grade': self._get_grade(total_score)
        }

    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A+ (Elite Scalper)"
        elif score >= 80:
            return "A (Excellent Scalper)"
        elif score >= 70:
            return "B (Good Scalper)"
        elif score >= 60:
            return "C (Improving)"
        elif score >= 50:
            return "D (Needs Work)"
        else:
            return "F (High Risk)"

    def _identify_improvements(self, cycle_number: int) -> List[str]:
        """Identify improvements from previous cycle"""
        if cycle_number == 1:
            return ["🆕 First learning cycle - establishing baseline"]

        improvements = []
        current = self.history['learning_cycles'][-1] if self.history['learning_cycles'] else None
        if not current:
            return improvements

        current_metrics = current['metrics']
        prev_win_rate = current_metrics['win_rate']
        prev_rr = current_metrics['risk_reward_ratio']
        prev_score = current['scalper_score']['total']

        # This will be compared in next cycle
        improvements.append(f"📊 Previous: {prev_win_rate:.1f}% win rate | R:R {prev_rr:.2f} | Score {prev_score:.1f}")

        return improvements

    def _generate_trading_tips(self, analysis: Dict, insights: Dict) -> List[str]:
        """Generate actionable trading tips based on current data"""
        tips = []
        winners = analysis.get('winners', [])
        losers = analysis.get('losers', [])

        # Tip 1: Entry timing
        if winners:
            avg_range = sum(w['range_30min'] for w in winners) / len(winners)
            tips.append(f"⏰ ENTRY TIMING: Best entries when 30min range ≥{avg_range:.2f}% (trending market)")

        # Tip 2: Position location
        if winners:
            avg_location = sum(w['price_location_pct'] for w in winners) / len(winners)
            if avg_location < 40:
                tips.append(f"📍 PRICE LOCATION: Enter LONG in lower {int(avg_location)}% of 2h range (don't chase highs)")
            elif avg_location > 60:
                tips.append(f"📍 PRICE LOCATION: Enter SHORT in upper {int(100-avg_location)}% of 2h range (don't short lows)")

        # Tip 3: Hold duration
        best_hold = analysis.get('best_hold_duration')
        if best_hold:
            tips.append(f"⏱️  HOLD TIME: Optimal exit at {best_hold} minutes (best win rate)")

        # Tip 4: What to avoid
        if losers:
            ranging_losses = len([l for l in losers if l['range_30min'] < 0.4])
            choppy_losses = len([l for l in losers if l['ribbon_flips_30min'] >= 3])

            if ranging_losses > len(losers) * 0.5:
                tips.append(f"🚫 AVOID: Ranging markets (<0.4% in 30min) caused {ranging_losses} losses")
            if choppy_losses > len(losers) * 0.3:
                tips.append(f"🚫 AVOID: Choppy ribbon (≥3 flips) caused {choppy_losses} losses")

        # Tip 5: Direction bias
        long_wins = len([w for w in winners if w['direction'] == 'LONG'])
        short_wins = len([w for w in winners if w['direction'] == 'SHORT'])
        if long_wins > short_wins * 1.5:
            tips.append(f"📈 DIRECTION: Favor LONG setups ({long_wins} wins vs {short_wins} SHORT wins)")
        elif short_wins > long_wins * 1.5:
            tips.append(f"📉 DIRECTION: Favor SHORT setups ({short_wins} wins vs {long_wins} LONG wins)")

        # Tip 6: Risk management
        if losers:
            max_loss = abs(min(l['pnl_pct'] for l in losers))
            if max_loss > 0.5:
                tips.append(f"⚠️  RISK: Tighten stop losses - max loss was {max_loss:.2f}% (target <0.3%)")

        return tips

    def _determine_strategy_changes(self, analysis: Dict, insights: Dict) -> List[str]:
        """Determine what strategy adjustments should be made"""
        changes = []
        winners = analysis.get('winners', [])
        losers = analysis.get('losers', [])
        win_rate = analysis.get('win_rate', 0)

        # Change 1: Adjust range filter
        if losers:
            ranging_pct = len([l for l in losers if l['range_30min'] < 0.4]) / len(losers) * 100
            if ranging_pct > 60:
                changes.append(f"🔧 TIGHTEN range filter: {ranging_pct:.0f}% of losses in ranging markets - increase minimum to 0.5%")

        # Change 2: Adjust ribbon stability filter
        if losers:
            choppy_pct = len([l for l in losers if l['ribbon_flips_30min'] >= 3]) / len(losers) * 100
            if choppy_pct > 40:
                changes.append(f"🔧 TIGHTEN choppy filter: {choppy_pct:.0f}% of losses with ≥3 flips - reduce max to 2 flips")

        # Change 3: Adjust hold time
        best_hold = analysis.get('best_hold_duration')
        best_hold_wr = analysis.get('best_hold_win_rate', 0)
        if best_hold and best_hold_wr > win_rate * 1.5:
            changes.append(f"🔧 ADJUST hold time: {best_hold} min shows {best_hold_wr:.1f}% win rate vs {win_rate:.1f}% overall - prioritize this duration")

        # Change 4: Direction bias
        if winners:
            long_wins = len([w for w in winners if w['direction'] == 'LONG'])
            short_wins = len([w for w in winners if w['direction'] == 'SHORT'])
            if long_wins > short_wins * 2:
                changes.append(f"🔧 DIRECTION bias: LONG showing {long_wins} wins vs {short_wins} SHORT - increase LONG confidence threshold")

        # Change 5: Win rate targets
        if win_rate < 15:
            changes.append("🔧 TIGHTEN all filters: Win rate <15% indicates too many bad entries - increase selectivity")
        elif win_rate > 30:
            changes.append("🔧 RELAX filters slightly: Win rate >30% indicates possibly missing good opportunities")

        return changes

    def _update_performance_summary(self, cycle: Dict):
        """Update overall performance summary with best metrics"""
        metrics = cycle['metrics']
        win_rate = metrics['win_rate']
        risk_reward = metrics['risk_reward_ratio']

        # Update highest win rate
        if win_rate > self.history['performance_summary']['highest_win_rate']:
            self.history['performance_summary']['highest_win_rate'] = win_rate
            self.history['performance_summary']['highest_win_rate_cycle'] = cycle['cycle_number']

        # Update best risk/reward
        if risk_reward > self.history['performance_summary']['best_risk_reward_ratio']:
            self.history['performance_summary']['best_risk_reward_ratio'] = risk_reward
            self.history['performance_summary']['best_rr_cycle'] = cycle['cycle_number']

        # Update most profitable setup
        if win_rate > 20 and risk_reward > 1.5:
            self.history['performance_summary']['most_profitable_setup'] = {
                'cycle': cycle['cycle_number'],
                'win_rate': win_rate,
                'risk_reward': risk_reward,
                'patterns': cycle['winning_patterns']
            }

    def _save_history(self):
        """Save training history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def generate_report(self) -> str:
        """Generate human-readable training report"""
        if not self.history['learning_cycles']:
            return "📊 No training cycles recorded yet"

        latest = self.history['learning_cycles'][-1]
        total_cycles = self.history['total_learning_cycles']

        report = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                     TRADING BOT TRAINING REPORT                             ║
║                    True Scalper - Maximize Profit, Minimize Risk            ║
╚════════════════════════════════════════════════════════════════════════════╝

📅 Cycle #{latest['cycle_number']} of {total_cycles} | {latest['timestamp'][:16]}

🎯 SCALPER PERFORMANCE SCORE: {latest['scalper_score']['total']:.1f}/100 - {latest['scalper_score']['grade']}
   ├─ Win Rate: {latest['scalper_score']['win_rate_component']:.1f}/40
   ├─ Speed: {latest['scalper_score']['speed_component']:.1f}/20
   ├─ Risk Management: {latest['scalper_score']['risk_management_component']:.1f}/20
   └─ Consistency: {latest['scalper_score']['consistency_component']:.1f}/20

📊 CURRENT METRICS:
   • Win Rate: {latest['metrics']['win_rate']:.1f}%
   • Risk/Reward: {latest['metrics']['risk_reward_ratio']:.2f}:1
   • Profit Factor: {latest['metrics']['profit_factor']:.2f}
   • Best Hold: {latest['metrics']['best_hold_duration']} minutes
   • Avg Winner: +{latest['metrics']['avg_winner_pnl']:.3f}%
   • Avg Loser: {latest['metrics']['avg_loser_pnl']:.3f}%

✅ WINNING PATTERNS:
   • 30min Range: {latest['winning_patterns']['avg_30min_range']:.2f}%
   • Price Location: {latest['winning_patterns']['avg_price_location']:.0f}% of 2h range
   • Ribbon Stability: {latest['winning_patterns']['avg_ribbon_flips']:.1f} flips
   • Best Direction: {latest['winning_patterns']['best_direction']}

❌ LOSING PATTERNS:
   • Ranging Losses: {latest['losing_patterns']['ranging_losses']}
   • Choppy Losses: {latest['losing_patterns']['choppy_losses']}
   • Worst Direction: {latest['losing_patterns']['worst_direction']}

💡 TRADING TIPS:
"""
        for i, tip in enumerate(latest['trading_tips'], 1):
            report += f"   {i}. {tip}\n"

        if latest['strategy_changes']:
            report += "\n🔧 STRATEGY ADJUSTMENTS:\n"
            for i, change in enumerate(latest['strategy_changes'], 1):
                report += f"   {i}. {change}\n"

        if latest['improvements_from_previous']:
            report += "\n📈 IMPROVEMENTS:\n"
            for improvement in latest['improvements_from_previous']:
                report += f"   • {improvement}\n"

        # Add all-time best
        summary = self.history['performance_summary']
        report += f"""
🏆 ALL-TIME BEST:
   • Highest Win Rate: {summary['highest_win_rate']:.1f}% (Cycle #{summary.get('highest_win_rate_cycle', 'N/A')})
   • Best Risk/Reward: {summary['best_risk_reward_ratio']:.2f}:1 (Cycle #{summary.get('best_rr_cycle', 'N/A')})

{'='*80}
"""
        return report

    def get_latest_cycle(self) -> Dict:
        """Get most recent learning cycle"""
        if not self.history['learning_cycles']:
            return None
        return self.history['learning_cycles'][-1]

    def get_strategy_evolution_summary(self) -> str:
        """Get summary of how strategy has evolved"""
        if not self.history['strategy_evolution']:
            return "No strategy changes yet"

        summary = "🔄 STRATEGY EVOLUTION:\n\n"
        for evolution in self.history['strategy_evolution'][-5:]:  # Last 5 changes
            summary += f"Cycle #{evolution['cycle']}: {evolution['timestamp'][:16]}\n"
            for change in evolution['changes']:
                summary += f"  • {change}\n"
            summary += "\n"

        return summary
