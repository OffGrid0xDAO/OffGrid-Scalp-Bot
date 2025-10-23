"""
Continuous Learning Module for Trading Bot
Runs backtests on recent data and generates training insights for Claude

Enhanced with Ultimate Analyzer for regime detection and wick analysis
NOW INCLUDES: Actual Trade Analysis from claude_decisions.csv
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import csv
from training_history import TrainingHistory

# Import actual trade learner
try:
    from actual_trade_learner import ActualTradeLearner
    ACTUAL_TRADE_LEARNER_AVAILABLE = True
except ImportError:
    ACTUAL_TRADE_LEARNER_AVAILABLE = False
    print("⚠️  Actual trade learner not available")

# Import optimal vs actual analyzer
try:
    from optimal_vs_actual_analyzer import OptimalVsActualAnalyzer
    OPTIMAL_ANALYZER_AVAILABLE = True
except ImportError:
    OPTIMAL_ANALYZER_AVAILABLE = False
    print("⚠️  Optimal analyzer not available")

# Import smart trade finder (realistic backtest with profit targets)
try:
    from smart_trade_finder import SmartTradeFinder
    SMART_TRADE_FINDER_AVAILABLE = True
except ImportError:
    SMART_TRADE_FINDER_AVAILABLE = False
    print("⚠️  Smart trade finder not available")

# Import ultimate analyzer for advanced analysis
try:
    from ultimate_backtest_analyzer import UltimateStrategyAnalyzer
    ULTIMATE_ANALYZER_AVAILABLE = True
except ImportError:
    ULTIMATE_ANALYZER_AVAILABLE = False
    print("⚠️  Ultimate analyzer not available - using basic analysis only")


class ContinuousLearning:
    """
    Analyzes recent trading data and generates training insights
    """

    def __init__(self, csv_5min_path='trading_data/ema_data_5min.csv',
                 csv_15min_path='trading_data/ema_data_15min.csv'):
        self.csv_5min = csv_5min_path
        self.csv_15min = csv_15min_path
        self.last_analysis_time = None
        self.training_insights = {
            'last_updated': None,
            'total_opportunities_analyzed': 0,
            'win_rate': 0,
            'best_hold_duration': None,
            'best_setups': [],
            'worst_setups': [],
            'key_lessons': [],
            # Enhanced insights from ultimate analyzer
            'current_regime': 'UNKNOWN',
            'regime_strategy': '',
            'wick_performance': {},
            'optimal_confidence_threshold': 0.85
        }
        self.history = TrainingHistory()  # Track training history

        # Initialize ultimate analyzer if available
        self.ultimate_analyzer = None
        if ULTIMATE_ANALYZER_AVAILABLE:
            try:
                self.ultimate_analyzer = UltimateStrategyAnalyzer(
                    data_5min_file=csv_5min_path,
                    data_15min_file=csv_15min_path
                )
                print("✅ Ultimate analyzer initialized for enhanced learning")
            except Exception as e:
                print(f"⚠️  Could not initialize ultimate analyzer: {e}")

    def should_run_analysis(self, hours_interval: int = 1) -> bool:
        """Check if enough time has passed since last analysis"""
        if self.last_analysis_time is None:
            return True

        time_since_last = datetime.now() - self.last_analysis_time
        return time_since_last.total_seconds() >= hours_interval * 3600

    def run_backtest_analysis(self, lookback_hours: int = 4) -> Dict:
        """
        Run backtest on recent data

        Args:
            lookback_hours: How many hours of recent data to analyze

        Returns:
            Dict with analysis results
        """
        print(f"\n🔬 Running backtest analysis on last {lookback_hours} hours...")

        # Load recent data
        data_5min = self._load_recent_data(self.csv_5min, lookback_hours)
        data_15min = self._load_recent_data(self.csv_15min, lookback_hours)

        if len(data_5min) < 100:
            print("⚠️  Not enough data for analysis yet")
            return None

        # Detect entry opportunities
        opportunities = self._detect_opportunities(data_5min, data_15min)

        if len(opportunities) == 0:
            print("⚠️  No entry opportunities found in recent data")
            return None

        # Simulate trades with multiple hold times
        trades = []
        for opp in opportunities:
            for hold_time in [5, 10, 15, 20, 30]:
                trade = self._simulate_trade(data_5min, opp, hold_time)
                if trade:
                    trades.append(trade)

        # Analyze results
        analysis = self._analyze_trades(trades)

        # Update training insights
        self._update_training_insights(analysis)

        # Record in training history
        cycle = self.history.add_learning_cycle(analysis, self.training_insights)

        self.last_analysis_time = datetime.now()

        print(f"✅ Analysis complete: {len(opportunities)} opportunities, {len(trades)} trades simulated")
        print(f"📊 Win rate: {analysis['win_rate']:.1f}% | Best hold: {analysis['best_hold_duration']} min")
        print(f"🎯 Scalper Score: {cycle['scalper_score']['total']:.1f}/100 - {cycle['scalper_score']['grade']}")

        # Run enhanced analysis if ultimate analyzer available
        if self.ultimate_analyzer:
            print("\n🚀 Running enhanced regime + wick analysis...")
            try:
                self._run_enhanced_analysis()
            except Exception as e:
                print(f"⚠️  Enhanced analysis error: {e}")

        return analysis

    def _run_enhanced_analysis(self):
        """
        Run ultimate analyzer for regime detection and wick analysis
        Updates training insights with regime-specific strategies
        """
        if not self.ultimate_analyzer:
            return

        print("📊 Loading data for regime analysis...")
        self.ultimate_analyzer.load_all_data()

        print("🔍 Detecting market regimes...")
        regimes = self.ultimate_analyzer.detect_market_regimes()

        print("🕯️  Analyzing wick patterns...")
        wicks = self.ultimate_analyzer.analyze_wick_patterns()

        print("📈 Analyzing EMA correlations...")
        self.ultimate_analyzer.analyze_ema_correlations()

        print("🎯 Generating optimal strategy...")
        strategy = self.ultimate_analyzer.generate_optimal_strategy()

        # Determine current regime (most recent)
        if regimes:
            current_regime = regimes[-1]['regime']
            self.training_insights['current_regime'] = current_regime
            print(f"📍 Current market regime: {current_regime}")

            # Get regime-specific strategy
            if current_regime in strategy['market_regime_rules']:
                regime_rules = strategy['market_regime_rules'][current_regime]
                self.training_insights['regime_strategy'] = regime_rules['recommendation']
                print(f"💡 Strategy: {regime_rules['recommendation'][:100]}...")
        else:
            self.training_insights['current_regime'] = 'UNKNOWN'

        # Update wick performance insights
        if wicks:
            # Group by type
            wick_stats = {}
            for wick in wicks:
                wick_type = wick['type']
                if wick_type not in wick_stats:
                    wick_stats[wick_type] = {'count': 0, 'winners': 0}
                wick_stats[wick_type]['count'] += 1
                if wick['winner']:
                    wick_stats[wick_type]['winners'] += 1

            # Calculate win rates
            for wick_type, stats in wick_stats.items():
                wr = (stats['winners'] / stats['count'] * 100) if stats['count'] > 0 else 0
                wick_stats[wick_type]['win_rate'] = wr

            self.training_insights['wick_performance'] = wick_stats
            print(f"🕯️  Wick analysis: {len(wicks)} opportunities detected")

        # Update optimal confidence threshold based on performance
        # If win rate is low, require higher confidence
        current_wr = self.training_insights.get('win_rate', 0)
        if current_wr < 50:
            self.training_insights['optimal_confidence_threshold'] = 0.90  # Stricter
        elif current_wr < 55:
            self.training_insights['optimal_confidence_threshold'] = 0.85  # Normal
        else:
            self.training_insights['optimal_confidence_threshold'] = 0.80  # Can be more aggressive

        print(f"🎯 Optimal confidence threshold: {self.training_insights['optimal_confidence_threshold']:.0%}")
        print("✅ Enhanced analysis complete!")

    def _load_recent_data(self, csv_path: str, lookback_hours: int) -> List[Dict]:
        """Load data from recent N hours"""
        data = []
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)

        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        timestamp = datetime.fromisoformat(row['timestamp'])
                        if timestamp >= cutoff_time:
                            data.append({
                                'timestamp': timestamp,
                                'price': float(row.get('price', 0)),
                                'state': row.get('ribbon_state', ''),
                                'raw_row': row
                            })
                    except:
                        continue
        except FileNotFoundError:
            print(f"⚠️  File not found: {csv_path}")
            return []

        return data

    def _detect_opportunities(self, data_5min: List[Dict], data_15min: List[Dict]) -> List[Dict]:
        """Detect ribbon flips to ALL_GREEN or ALL_RED"""
        opportunities = []
        last_valid_state = None

        for i, point in enumerate(data_5min):
            state = point['state'].lower()

            # Skip unknown/mixed states
            if 'unknown' in state or ('mixed' in state and 'all' not in state):
                continue

            # Detect flips
            direction = None
            is_entry = False

            if 'all_green' in state:
                if last_valid_state is None or 'all_green' not in last_valid_state:
                    direction = 'LONG'
                    is_entry = True
            elif 'all_red' in state:
                if last_valid_state is None or 'all_red' not in last_valid_state:
                    direction = 'SHORT'
                    is_entry = True

            if is_entry:
                # Calculate entry conditions
                range_30min = self._calculate_range(data_5min, i, 30)
                range_15min = self._calculate_range(data_5min, i, 15)
                range_2h = self._calculate_range(data_5min, i, 120)
                ribbon_flips = self._count_flips(data_5min, i, 30)
                price_location = self._calculate_price_location(data_5min, i, 120)

                opportunities.append({
                    'index': i,
                    'timestamp': point['timestamp'],
                    'direction': direction,
                    'entry_price': point['price'],
                    'state': state,
                    'range_30min': range_30min,
                    'range_15min': range_15min,
                    'range_2h': range_2h,
                    'ribbon_flips_30min': ribbon_flips,
                    'price_location_pct': price_location
                })

            # Update last valid state
            if 'all_green' in state or 'all_red' in state:
                last_valid_state = state

        return opportunities

    def _calculate_range(self, data: List[Dict], index: int, minutes: int) -> float:
        """Calculate price range % for time window"""
        points_needed = minutes * 6  # 6 points per minute (10-second intervals)
        start_idx = max(0, index - points_needed)
        window = data[start_idx:index + 1]

        prices = [d['price'] for d in window if d['price'] > 0]
        if not prices or len(prices) < 2:
            return 0

        high = max(prices)
        low = min(prices)

        if low == 0:
            return 0

        return ((high - low) / low) * 100

    def _count_flips(self, data: List[Dict], index: int, minutes: int) -> int:
        """Count ribbon flips in time window"""
        points_needed = minutes * 6
        start_idx = max(0, index - points_needed)
        window = data[start_idx:index + 1]

        flips = 0
        last_direction = None

        for point in window:
            state = point['state'].lower()

            if 'green' in state:
                direction = 'green'
            elif 'red' in state:
                direction = 'red'
            else:
                continue

            if last_direction and last_direction != direction:
                flips += 1

            last_direction = direction

        return flips

    def _calculate_price_location(self, data: List[Dict], index: int, minutes: int) -> float:
        """Calculate where price is in the range (0-100%)"""
        points_needed = minutes * 6
        start_idx = max(0, index - points_needed)
        window = data[start_idx:index + 1]

        prices = [d['price'] for d in window if d['price'] > 0]
        if not prices or len(prices) < 2:
            return 50

        high = max(prices)
        low = min(prices)
        current = data[index]['price']

        if high == low:
            return 50

        return ((current - low) / (high - low)) * 100

    def _simulate_trade(self, data: List[Dict], opp: Dict, hold_minutes: int) -> Dict:
        """Simulate a trade from entry opportunity"""
        entry_idx = opp['index']
        entry_price = opp['entry_price']
        direction = opp['direction']

        # Calculate exit index
        points_to_hold = hold_minutes * 6  # 6 points per minute
        exit_idx = entry_idx + points_to_hold

        if exit_idx >= len(data):
            return None  # Not enough data to complete trade

        exit_price = data[exit_idx]['price']

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        return {
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'hold_minutes': hold_minutes,
            'pnl_pct': pnl_pct,
            'is_winner': pnl_pct > 0,
            'range_30min': opp['range_30min'],
            'range_15min': opp['range_15min'],
            'range_2h': opp['range_2h'],
            'ribbon_flips_30min': opp['ribbon_flips_30min'],
            'price_location_pct': opp['price_location_pct'],
            'timestamp': opp['timestamp']
        }

    def _analyze_trades(self, trades: List[Dict]) -> Dict:
        """Analyze trade results and extract patterns"""
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'best_hold_duration': None,
                'winners': [],
                'losers': []
            }

        winners = [t for t in trades if t['is_winner']]
        losers = [t for t in trades if not t['is_winner']]

        win_rate = (len(winners) / len(trades)) * 100 if trades else 0

        # Find best hold duration
        hold_times = {}
        for trade in trades:
            hold = trade['hold_minutes']
            if hold not in hold_times:
                hold_times[hold] = {'wins': 0, 'total': 0, 'pnl': 0}
            hold_times[hold]['total'] += 1
            hold_times[hold]['pnl'] += trade['pnl_pct']
            if trade['is_winner']:
                hold_times[hold]['wins'] += 1

        best_hold = None
        best_win_rate = 0
        for hold, stats in hold_times.items():
            wr = (stats['wins'] / stats['total']) * 100 if stats['total'] > 0 else 0
            if wr > best_win_rate:
                best_win_rate = wr
                best_hold = hold

        return {
            'total_trades': len(trades),
            'winners': winners,
            'losers': losers,
            'win_rate': win_rate,
            'best_hold_duration': best_hold,
            'best_hold_win_rate': best_win_rate,
            'hold_times': hold_times
        }

    def _update_training_insights(self, analysis: Dict):
        """Update training insights with new analysis"""
        self.training_insights['last_updated'] = datetime.now().isoformat()
        self.training_insights['total_opportunities_analyzed'] = analysis['total_trades']
        self.training_insights['win_rate'] = analysis['win_rate']
        self.training_insights['best_hold_duration'] = analysis['best_hold_duration']

        # Analyze winning patterns
        winners = analysis['winners']
        losers = analysis['losers']

        best_setups = []
        worst_setups = []
        key_lessons = []

        if winners:
            avg_winner_range = sum(w['range_30min'] for w in winners) / len(winners)
            avg_winner_location = sum(w['price_location_pct'] for w in winners) / len(winners)
            avg_winner_flips = sum(w['ribbon_flips_30min'] for w in winners) / len(winners)

            best_setups.append(f"30min range ≥{avg_winner_range:.2f}% (trending markets)")
            best_setups.append(f"Price location ~{avg_winner_location:.0f}% of 2h range")
            best_setups.append(f"Ribbon flips ≤{avg_winner_flips:.1f} (stable)")

            # Count specific patterns
            big_moves = len([w for w in winners if w['range_30min'] >= 0.8])
            lower_entries = len([w for w in winners if w['price_location_pct'] < 40])
            stable_ribbon = len([w for w in winners if w['ribbon_flips_30min'] <= 1])

            if big_moves > 0:
                best_setups.append(f"Big moves (≥0.8%): {big_moves} winners")
            if lower_entries > 0:
                key_lessons.append(f"✅ ENTER IN LOWER 40% OF RANGE: {lower_entries} wins")
            if stable_ribbon > 0:
                key_lessons.append(f"✅ STABLE RIBBON (≤1 flip): {stable_ribbon} wins")

        if losers:
            avg_loser_range = sum(l['range_30min'] for l in losers) / len(losers)
            avg_loser_flips = sum(l['ribbon_flips_30min'] for l in losers) / len(losers)

            # Count specific patterns
            ranging = len([l for l in losers if l['range_30min'] < 0.4])
            choppy = len([l for l in losers if l['ribbon_flips_30min'] >= 3])

            if ranging > 0:
                worst_setups.append(f"Ranging (<0.4%): {ranging} losses")
                key_lessons.append(f"❌ SKIP RANGING MARKETS: {ranging} losses avoided if filtered")
            if choppy > 0:
                worst_setups.append(f"Choppy (≥3 flips): {choppy} losses")
                key_lessons.append(f"❌ SKIP CHOPPY RIBBON: {choppy} losses avoided if filtered")

        # Add hold duration lesson
        if analysis['best_hold_duration']:
            key_lessons.append(
                f"⏱️  OPTIMAL HOLD: {analysis['best_hold_duration']} minutes "
                f"({analysis['best_hold_win_rate']:.1f}% win rate)"
            )

        self.training_insights['best_setups'] = best_setups
        self.training_insights['worst_setups'] = worst_setups
        self.training_insights['key_lessons'] = key_lessons

    def load_actual_trade_insights(self) -> Dict:
        """Load insights from actual executed trades"""
        if not ACTUAL_TRADE_LEARNER_AVAILABLE:
            return None

        try:
            learner = ActualTradeLearner()
            trades = learner.load_actual_trades()

            if not trades or len(trades) < 5:
                return None

            return learner.analyze_trades(trades)
        except Exception as e:
            print(f"⚠️  Could not load actual trade insights: {e}")
            return None

    def load_optimal_comparison(self) -> Dict:
        """Load optimal vs actual trade comparison"""
        if not OPTIMAL_ANALYZER_AVAILABLE:
            return None

        try:
            analyzer = OptimalVsActualAnalyzer()
            candles = analyzer.load_candlestick_data()
            actual_trades = analyzer.load_actual_trades()

            if not candles or len(candles) < 100:
                return None

            optimal_trades = analyzer.find_optimal_trades(candles)

            if not optimal_trades:
                return None

            comparison = analyzer.compare_trades(optimal_trades, actual_trades)
            return comparison
        except Exception as e:
            print(f"⚠️  Could not load optimal comparison: {e}")
            return None

    def load_smart_backtest(self) -> Dict:
        """Load smart trade finder backtest (realistic profit targets)"""
        if not SMART_TRADE_FINDER_AVAILABLE:
            return None

        try:
            finder = SmartTradeFinder(
                profit_target_pct=0.3,  # 0.3% profit target (realistic for scalping)
                stop_loss_pct=0.15,     # 0.15% stop loss
                max_hold_minutes=45,    # Max 45 min hold
                min_trade_spacing_minutes=20  # Min 20 min between trades
            )

            # Load candlestick data
            candles_5min = finder.load_candlestick_data('candlesticks_5min.csv')
            candles_15min = finder.load_candlestick_data('candlesticks_15min.csv')

            if not candles_5min or len(candles_5min) < 100:
                return None

            # Run backtest
            trades = finder.backtest_strategy(candles_5min, candles_15min)

            if not trades:
                return None

            # Analyze results
            analysis = finder.analyze_results(trades)

            # Add trade details for top trades
            analysis['top_trades'] = sorted(
                [t.to_dict() for t in trades if t.pnl_dollars > 0],
                key=lambda x: x['pnl_dollars'],
                reverse=True
            )[:5]  # Top 5 profitable trades

            return analysis
        except Exception as e:
            print(f"⚠️  Could not load smart backtest: {e}")
            return None

    def get_training_prompt_addition(self) -> str:
        """
        Generate prompt text to add to Claude's system prompt
        This contains: ACTUAL TRADE RESULTS + OPTIMAL TRADE COMPARISON + Backtest insights
        """
        # Load insights
        actual_insights = self.load_actual_trade_insights()
        optimal_comparison = self.load_optimal_comparison()
        smart_backtest = self.load_smart_backtest()

        prompt = ""

        # Add OPTIMAL vs ACTUAL comparison (HIGHEST PRIORITY!)
        if optimal_comparison:
            prompt += f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                   OPTIMAL VS ACTUAL PERFORMANCE ANALYSIS                      ║
║              (What you COULD have made vs what you actually made)             ║
╚══════════════════════════════════════════════════════════════════════════════╝

🎯 **PERFORMANCE GAP:**
   Optimal Trades (Perfect Timing): {optimal_comparison['optimal_trades']}
   Your Actual Trades: {optimal_comparison['actual_trades']}
   Missed Opportunities: {optimal_comparison['missed_opportunities']}

💰 **P&L GAP:**
   Optimal P&L: ${optimal_comparison['optimal_pnl']:.2f} ({optimal_comparison['optimal_win_rate']:.0f}% win rate)
   Your Actual P&L: ${optimal_comparison['actual_pnl']:.2f} ({optimal_comparison['actual_win_rate']:.0f}% win rate)
   💸 YOU LEFT ON THE TABLE: ${optimal_comparison['missed_pnl']:.2f}

🎨 **TOP PATTERNS IN OPTIMAL TRADES (These made the most money!):**
"""
            for pattern in optimal_comparison['optimal_patterns'][:3]:
                prompt += f"   ✅ {pattern['signature']}: ${pattern['avg_pnl']:.2f} avg ({pattern['count']} trades)\n"

            prompt += f"""
⚠️  **CRITICAL: Focus on these patterns! They made ${optimal_comparison['avg_optimal_pnl']:.2f} per trade vs your ${optimal_comparison['avg_actual_pnl']:.2f}**
"""

        # Add actual trade performance if available
        if actual_insights:
            prompt += f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                     ACTUAL TRADE PERFORMANCE ANALYSIS                         ║
║                    (Learn from your real trading history!)                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 **REAL TRADING RESULTS:**
   Total Actual Trades: {actual_insights['total_trades']}
   Profitable: {actual_insights['profitable_trades']} ({actual_insights['win_rate']:.1f}% win rate)
   Total P&L: ${actual_insights['total_pnl']:.2f}

📈 **DIRECTION PERFORMANCE:**
   LONG: {actual_insights['long_stats']['total']} trades, {actual_insights['long_stats']['win_rate']:.1f}% win rate (${actual_insights['long_stats']['total_pnl']:.2f})
   SHORT: {actual_insights['short_stats']['total']} trades, {actual_insights['short_stats']['win_rate']:.1f}% win rate (${actual_insights['short_stats']['total_pnl']:.2f})

🎨 **EMA PATTERN PERFORMANCE (From Your Actual Trades):**
"""
            if actual_insights.get('ema_patterns'):
                for pattern in actual_insights['ema_patterns'][:3]:  # Top 3
                    emoji = "✅" if pattern['win_rate'] >= 50 else "⚠️"
                    prompt += f"   {emoji} {pattern['signature']}: {pattern['win_rate']:.0f}% WR ({pattern['total']} trades)\n"
            else:
                prompt += "   Collecting pattern data...\n"

            prompt += f"""
🎓 **KEY LESSONS FROM YOUR ACTUAL TRADES:**
"""
            for lesson in actual_insights['key_lessons']:
                prompt += f"   • {lesson}\n"

            prompt += "\n⚠️  **APPLY THESE LESSONS TO AVOID REPEATING MISTAKES!**\n"

        # Add smart backtest results (realistic profit targets)
        if smart_backtest:
            prompt += f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                    REALISTIC BACKTEST (With Profit Targets)                   ║
║           (What the strategy would have made with fixed exits)                ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 **BACKTEST RESULTS (0.3% Profit Target, 0.15% Stop Loss):**
   Total Trades: {smart_backtest['total_trades']}
   Profitable: {smart_backtest['profitable_trades']} ({smart_backtest['win_rate']:.1f}% win rate)
   Total P&L: ${smart_backtest['total_pnl_dollars']:.2f}
   Avg P&L per Trade: ${smart_backtest['avg_profit_per_trade']:.2f}
   Avg Hold Time: {smart_backtest['avg_hold_time']:.1f} minutes

📈 **DIRECTION BREAKDOWN:**
   LONG Trades: {smart_backtest['long_trades']}
   SHORT Trades: {smart_backtest['short_trades']}

🎯 **EXIT REASONS (What worked best):**
"""
            for reason, stats in smart_backtest.get('exit_reasons', {}).items():
                win_rate = (stats['profitable'] / stats['count'] * 100) if stats['count'] > 0 else 0
                emoji = "✅" if win_rate >= 50 else "⚠️" if win_rate >= 30 else "❌"
                prompt += f"   {emoji} {reason}: {stats['count']} trades ({win_rate:.0f}% win rate)\n"

            if smart_backtest.get('top_trades'):
                prompt += f"""
💰 **TOP 3 PROFITABLE TRADES (Learn from these!):**
"""
                for i, trade in enumerate(smart_backtest['top_trades'][:3], 1):
                    prompt += f"   {i}. {trade['direction']} @ ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} (+${trade['pnl_dollars']:.2f}, {trade['hold_minutes']}min)\n"
                    prompt += f"      Ribbon: {trade['entry_ribbon_5min']} (5min) + {trade['entry_ribbon_15min']} (15min)\n"

            prompt += f"""
⚠️  **KEY INSIGHT: Backtest shows {smart_backtest['win_rate']:.0f}% win rate is achievable with proper exits!**
"""

        # Add simulated backtest insights
        if not self.training_insights['last_updated']:
            return prompt

        insights = self.training_insights

        prompt += f"""

📚 **SIMULATED BACKTEST ANALYSIS** (Updated: {insights['last_updated'][:16]})

Based on analysis of {insights['total_opportunities_analyzed']} simulated trades:

🎯 **SIMULATED WIN RATE: {insights['win_rate']:.1f}%**

⏱️  **OPTIMAL HOLD TIME: {insights['best_hold_duration']} minutes**
"""

        # Add regime-specific strategy if available
        if insights.get('current_regime') and insights.get('regime_strategy'):
            prompt += f"""
🌊 **CURRENT MARKET REGIME: {insights['current_regime']}**

💡 **REGIME-ADAPTIVE STRATEGY:**
{insights['regime_strategy']}
"""

        # Add wick performance if available
        if insights.get('wick_performance'):
            prompt += "\n\n🕯️  **WICK ENTRY PERFORMANCE:**"
            for wick_type, stats in insights['wick_performance'].items():
                wr = stats.get('win_rate', 0)
                count = stats.get('count', 0)
                if count > 0:
                    prompt += f"\n   • {wick_type}: {wr:.0f}% WR ({count} samples)"

        # Add optimal confidence threshold
        if insights.get('optimal_confidence_threshold'):
            conf = insights['optimal_confidence_threshold']
            prompt += f"\n\n🎯 **RECOMMENDED CONFIDENCE THRESHOLD: {conf:.0%}**"
            if conf >= 0.90:
                prompt += " (Strict - low win rate detected)"
            elif conf >= 0.85:
                prompt += " (Normal - moderate performance)"
            else:
                prompt += " (Relaxed - high win rate achieved)"

        prompt += "\n\n✅ **PROVEN WINNING SETUPS:**"
        for setup in insights['best_setups']:
            prompt += f"\n   • {setup}"

        if insights['worst_setups']:
            prompt += "\n\n❌ **AVOID THESE SETUPS:**"
            for setup in insights['worst_setups']:
                prompt += f"\n   • {setup}"

        if insights['key_lessons']:
            prompt += "\n\n🔥 **KEY LESSONS FROM RECENT DATA:**"
            for lesson in insights['key_lessons']:
                prompt += f"\n   {lesson}"

        prompt += "\n\n**ADAPT YOUR STRATEGY TO THE CURRENT REGIME AND USE THESE INSIGHTS!**\n"

        return prompt

    def save_insights_to_file(self, filepath='training_insights.json'):
        """Save current insights to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.training_insights, f, indent=2)
        print(f"💾 Training insights saved to {filepath}")

    def get_training_report(self) -> str:
        """Generate detailed training report"""
        return self.history.generate_report()

    def get_strategy_evolution(self) -> str:
        """Get strategy evolution summary"""
        return self.history.get_strategy_evolution_summary()
