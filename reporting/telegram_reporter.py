#!/usr/bin/env python3
"""
Telegram Reporter

Sends beautiful formatted optimization reports to Telegram
"""

import os
from typing import Dict, List
from datetime import datetime


class TelegramReporter:
    """
    Send formatted reports to Telegram

    Beautiful 3-way comparison reports showing:
    - Optimal trades (perfect hindsight)
    - Backtest trades (strategy simulation)
    - Actual trades (live execution)
    """

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram reporter

        Args:
            bot_token: Telegram bot token (or from env TELEGRAM_BOT_TOKEN)
            chat_id: Telegram chat ID (or from env TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        # Check if credentials available
        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            try:
                import requests
                self.requests = requests
            except ImportError:
                print("⚠️  Telegram reporting disabled - install 'requests' package")
                self.enabled = False

    def send_optimization_report(
        self,
        optimal_results: Dict,
        backtest_results: Dict,
        actual_results: Dict = None,
        gap_analysis: Dict = None,
        iteration: int = 0,
        planned_changes: Dict = None
    ) -> bool:
        """
        Send complete optimization report

        Args:
            optimal_results: Results from optimal trade finder
            backtest_results: Results from backtest engine
            actual_results: Results from live trading (optional)
            gap_analysis: Gap analysis results
            iteration: Current iteration number
            planned_changes: Rule changes being applied

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            print("⚠️  Telegram reporting disabled - credentials not set")
            return False

        # Generate report text
        report = self._format_optimization_report(
            optimal_results,
            backtest_results,
            actual_results,
            gap_analysis,
            iteration,
            planned_changes
        )

        # Send to Telegram
        return self._send_message(report)

    def _format_optimization_report(
        self,
        optimal_results: Dict,
        backtest_results: Dict,
        actual_results: Dict,
        gap_analysis: Dict,
        iteration: int,
        planned_changes: Dict
    ) -> str:
        """Format beautiful 3-way comparison report"""

        # Extract metrics
        optimal_trades = len(optimal_results) if optimal_results else 0
        # For optimal: show average profit per trade
        optimal_avg_profit = sum(t['profit_pct'] for t in optimal_results) / optimal_trades if optimal_trades > 0 else 0
        optimal_avg_hold = sum(t['candles_held'] for t in optimal_results) / optimal_trades if optimal_trades > 0 else 0

        backtest_metrics = backtest_results.get('metrics', {})
        backtest_trades = backtest_metrics.get('total_trades', 0)
        # For backtest: show total portfolio return
        backtest_total_return = backtest_metrics.get('total_return', 0)
        # Also calculate average profit per trade for comparison
        backtest_avg_profit = backtest_total_return / backtest_trades if backtest_trades > 0 else 0
        backtest_win_rate = backtest_metrics.get('win_rate', 0)
        backtest_avg_hold = 0  # TODO: calculate from trades

        actual_trades = 0 if not actual_results else actual_results.get('total_trades', 0)
        actual_pnl = 0 if not actual_results else actual_results.get('total_pnl', 0)
        actual_win_rate = 0 if not actual_results else actual_results.get('win_rate', 0)

        # Calculate gaps (CORRECTED LOGIC)
        # Trade Gap: negative = under-trading (backtest < optimal), positive = over-trading
        trade_gap = backtest_trades - optimal_trades

        # PnL Gap: Compare total returns (both should be portfolio-level)
        optimal_total_return = sum(t['profit_pct'] for t in optimal_results) if optimal_results else 0
        pnl_gap = backtest_total_return - optimal_total_return  # negative = missing profit

        # Capture Rate: % of optimal profit we captured
        capture_rate = (backtest_total_return / optimal_total_return * 100) if optimal_total_return > 0 else 0

        backtest_actual_gap = backtest_trades - actual_trades

        # Generate key findings
        findings = self._generate_findings(
            optimal_results,
            backtest_results,
            actual_results,
            gap_analysis
        )

        # Build report
        report = f"""🔧 OPTIMIZATION CYCLE {iteration} COMPLETE 🔧

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 3-WAY PERFORMANCE COMPARISON

🥇 OPTIMAL TRADES (Perfect Hindsight)
├ Trades: {optimal_trades}
├ Total Return: {optimal_total_return:.2f}%
├ Avg Profit/Trade: {optimal_avg_profit:.2f}%
├ Avg Hold: {optimal_avg_hold:.1f} candles
└ Win Rate: 100% (by definition)

🥈 BACKTEST TRADES (Current Rules)
├ Trades: {backtest_trades}
├ Total Return: {backtest_total_return:.2f}%
├ Avg Profit/Trade: {backtest_avg_profit:.2f}%
├ Win Rate: {backtest_win_rate:.1f}%
├ Profit Factor: {backtest_metrics.get('profit_factor', 0):.2f}
└ Max Drawdown: {backtest_metrics.get('max_drawdown', 0):.2f}%

🥉 ACTUAL TRADES (Live Execution)
├ Trades: {actual_trades}
├ PnL: {actual_pnl:.2f}%
└ Win Rate: {actual_win_rate:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 GAP ANALYSIS

📉 Optimal → Backtest Gap
├ Trade Gap: {trade_gap:+d} trades ({('OVER-TRADING' if trade_gap > 0 else 'UNDER-TRADING')})
├ PnL Gap: {pnl_gap:.2f}% ({('capturing less' if pnl_gap < 0 else 'outperforming')})
└ Capture Rate: {capture_rate:.1f}%

⚠️ Backtest → Actual Gap
├ Execution Diff: {backtest_actual_gap:+d} trades
└ Status: {'✅ Aligned' if abs(backtest_actual_gap) < 5 else '⚠️ Needs attention'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 KEY FINDINGS
"""

        # Add findings
        for i, finding in enumerate(findings, 1):
            report += f"{i}. {finding}\n"

        # Add planned changes if any
        if planned_changes:
            report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️ RULE IMPROVEMENTS PLANNED
"""
            for key, value in planned_changes.items():
                old_value = "current"  # TODO: get from params
                report += f"\n• {key}: {old_value} → {value}"

        report += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report

    def _generate_findings(
        self,
        optimal_results: Dict,
        backtest_results: Dict,
        actual_results: Dict,
        gap_analysis: Dict
    ) -> List[str]:
        """Generate intelligent findings based on results"""
        findings = []

        optimal_trades = len(optimal_results) if optimal_results else 0
        backtest_trades = backtest_results.get('metrics', {}).get('total_trades', 0)
        actual_trades = 0 if not actual_results else actual_results.get('total_trades', 0)

        backtest_win_rate = backtest_results.get('metrics', {}).get('win_rate', 0)
        backtest_pnl = backtest_results.get('metrics', {}).get('total_return', 0)
        optimal_pnl = sum(t['profit_pct'] for t in optimal_results) if optimal_results else 0

        # Finding 1: Execution status
        if actual_trades == 0 and backtest_trades > 0:
            findings.append(
                f"🚨 CRITICAL: Zero actual trades vs {backtest_trades} backtest trades. "
                "Bot execution failure - check API connectivity and parameter sync."
            )
        elif abs(actual_trades - backtest_trades) > backtest_trades * 0.1:
            findings.append(
                f"⚠️ Execution drift: {abs(actual_trades - backtest_trades)} trade difference. "
                "Live conditions differ from backtest assumptions."
            )
        else:
            findings.append("✅ Execution aligned: Live trading matches backtest expectations.")

        # Finding 2: Over/Under trading (CORRECTED LOGIC)
        if optimal_trades > 0:
            trade_ratio = backtest_trades / optimal_trades

            if trade_ratio > 2.0:  # Taking more than 2x optimal trades
                findings.append(
                    f"🔴 OVER-TRADING: Taking {trade_ratio:.1f}x more trades than optimal "
                    f"({backtest_trades} vs {optimal_trades}). Filters too loose - catching low-quality signals."
                )
            elif trade_ratio < 0.5:  # Taking less than 50% of optimal trades
                findings.append(
                    f"🟡 UNDER-TRADING: Only capturing {trade_ratio:.0%} of optimal trades "
                    f"({backtest_trades} vs {optimal_trades}). Filters too strict - missing opportunities."
                )
            else:
                findings.append(
                    f"✅ Trade frequency balanced: {backtest_trades} trades vs {optimal_trades} optimal ({trade_ratio:.1f}x ratio)"
                )
        else:
            findings.append(
                f"✅ Good trade frequency: {backtest_trades} trades is reasonable vs {optimal_trades} optimal."
            )

        # Finding 3: Optimal trade quality
        if optimal_trades > 0:
            optimal_avg_profit = optimal_pnl / optimal_trades
            if optimal_avg_profit > 2.0:
                findings.append(
                    f"🎯 EXCELLENT OPTIMAL PATTERNS: {optimal_trades} trades averaged {optimal_avg_profit:.2f}% profit. "
                    "High-probability setups exist - we need to identify their characteristics."
                )
            else:
                findings.append(
                    f"⚠️ Marginal optimal performance: {optimal_avg_profit:.2f}% average suggests "
                    "market conditions are challenging."
                )

        # Finding 4: Win rate analysis
        if backtest_win_rate < 50:
            findings.append(
                f"🔴 LOW WIN RATE: {backtest_win_rate:.1f}% suggests strategy is not working. "
                "Major parameter adjustment needed."
            )
        elif backtest_win_rate < 55:
            findings.append(
                f"🟡 Baseline win rate: {backtest_win_rate:.1f}% needs improvement through optimization."
            )
        elif backtest_win_rate >= 55 and backtest_win_rate < 65:
            findings.append(
                f"✅ Good win rate: {backtest_win_rate:.1f}% is solid. Optimize for 65%+ target."
            )
        else:
            findings.append(
                f"🎉 EXCELLENT WIN RATE: {backtest_win_rate:.1f}% exceeds target! Consider tightening for quality."
            )

        # Finding 5: Capture rate
        capture_rate = (backtest_pnl / optimal_pnl * 100) if optimal_pnl > 0 else 0
        if capture_rate < 30:
            findings.append(
                f"🔴 LOW CAPTURE RATE: Only {capture_rate:.1f}% of optimal profit captured. "
                "Missing best setups or exiting too early."
            )
        elif capture_rate < 60:
            findings.append(
                f"🟡 Moderate capture: {capture_rate:.1f}% of optimal profit. Room for improvement."
            )
        else:
            findings.append(
                f"✅ Strong capture: {capture_rate:.1f}% of optimal profit achieved!"
            )

        return findings

    def _send_message(self, text: str) -> bool:
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }

            response = self.requests.post(url, data=data)

            if response.status_code == 200:
                print("✅ Report sent to Telegram")
                return True
            else:
                print(f"❌ Failed to send to Telegram: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error sending to Telegram: {e}")
            return False

    def send_simple_message(self, message: str) -> bool:
        """Send a simple text message"""
        if not self.enabled:
            return False
        return self._send_message(message)


if __name__ == '__main__':
    """Test Telegram reporter"""
    print("Telegram Reporter - Testing")

    reporter = TelegramReporter()

    if not reporter.enabled:
        print("\n⚠️  Telegram not configured")
        print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        print("   Or pass them to TelegramReporter(bot_token, chat_id)")
    else:
        print("✅ Telegram configured")

        # Send test message
        test = reporter.send_simple_message("🤖 Trading Bot Test - Telegram connection working!")
        if test:
            print("✅ Test message sent successfully")
        else:
            print("❌ Test message failed")
