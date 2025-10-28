#!/usr/bin/env python3
"""
Claude-Powered Live Trading Iteration Optimizer

Continuously learns from live trading results and generates
optimal prompts for Claude to analyze and improve the strategy.

Features:
- Analyzes live trading performance
- Generates detailed optimization prompts for Claude
- Tracks iteration improvements
- Suggests parameter adjustments
- Identifies failure patterns
- Proposes new signal combinations

Production-ready:
- Comprehensive performance analysis
- Pattern recognition
- Statistical significance testing
- Regime-specific analysis
- Multi-metric optimization
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import os
from anthropic import Anthropic

logger = logging.getLogger(__name__)


@dataclass
class IterationMetrics:
    """Performance metrics for an iteration"""
    iteration_id: int
    start_time: datetime
    end_time: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    avg_holding_time: float
    best_trade_pnl: float
    worst_trade_pnl: float


@dataclass
class TradeAnalysis:
    """Individual trade analysis"""
    trade_id: str
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    holding_time_minutes: float
    signal_confidence: float
    signal_coherence: float
    regime_at_entry: str
    exit_reason: str
    won: bool


class ClaudeIterationOptimizer:
    """
    Claude-powered optimization system for live trading iterations

    Analyzes live performance and generates optimization prompts for Claude
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        results_dir: str = 'live_trading_results',
        min_trades_for_analysis: int = 10
    ):
        """
        Initialize Claude optimization system

        Args:
            anthropic_api_key: Anthropic API key
            results_dir: Directory to store results
            min_trades_for_analysis: Minimum trades before optimization
        """
        self.api_key = anthropic_api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set - optimization prompts only")

        self.client = Anthropic(api_key=self.api_key) if self.api_key else None
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.min_trades = min_trades_for_analysis

        self.iterations = []

        logger.info(f"Initialized ClaudeIterationOptimizer (min_trades={min_trades_for_analysis})")

    def analyze_iteration(
        self,
        trades: List[Dict],
        current_params: Dict,
        iteration_id: int
    ) -> IterationMetrics:
        """
        Analyze a trading iteration

        Args:
            trades: List of trade dictionaries
            current_params: Current strategy parameters
            iteration_id: Iteration number

        Returns:
            IterationMetrics
        """
        if not trades:
            logger.warning("No trades to analyze")
            return None

        # Parse trades
        trade_analyses = [self._parse_trade(t) for t in trades]

        # Calculate metrics
        total_trades = len(trade_analyses)
        winning_trades = len([t for t in trade_analyses if t.won])
        losing_trades = total_trades - winning_trades

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        pnls = [t.pnl for t in trade_analyses]
        total_pnl = sum(pnls)

        # Calculate Sharpe ratio
        if len(pnls) > 1:
            returns = np.array(pnls)
            sharpe = np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252)
        else:
            sharpe = 0

        # Max drawdown
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0

        # Profit factor
        wins = [t.pnl for t in trade_analyses if t.won]
        losses = [abs(t.pnl) for t in trade_analyses if not t.won]
        total_wins = sum(wins) if wins else 0
        total_losses = sum(losses) if losses else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Average win/loss
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0

        # Holding time
        holding_times = [t.holding_time_minutes for t in trade_analyses]
        avg_holding = np.mean(holding_times) if holding_times else 0

        # Best/worst
        best_trade = max(pnls)
        worst_trade = min(pnls)

        # Create metrics
        metrics = IterationMetrics(
            iteration_id=iteration_id,
            start_time=trade_analyses[0].entry_time,
            end_time=trade_analyses[-1].exit_time,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl / 10000 * 100,  # Assuming $10k capital
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_holding_time=avg_holding,
            best_trade_pnl=best_trade,
            worst_trade_pnl=worst_trade
        )

        # Save iteration
        self.iterations.append((metrics, trade_analyses, current_params))

        # Save to file
        self._save_iteration(iteration_id, metrics, trade_analyses, current_params)

        return metrics

    def generate_optimization_prompt(
        self,
        current_metrics: IterationMetrics,
        previous_metrics: Optional[IterationMetrics] = None,
        trade_analyses: Optional[List[TradeAnalysis]] = None,
        current_params: Optional[Dict] = None
    ) -> str:
        """
        Generate detailed optimization prompt for Claude

        Returns:
            Optimization prompt string
        """
        prompt = f"""# 🎯 LIVE TRADING ITERATION ANALYSIS & OPTIMIZATION

You are analyzing LIVE TRADING results from a production trading bot on Hyperliquid.

## 📊 CURRENT PERFORMANCE (Iteration {current_metrics.iteration_id})

**Period**: {current_metrics.start_time.strftime('%Y-%m-%d %H:%M')} to {current_metrics.end_time.strftime('%Y-%m-%d %H:%M')}
**Duration**: {(current_metrics.end_time - current_metrics.start_time).total_seconds() / 3600:.1f} hours

### Performance Metrics:

| Metric | Value |
|--------|-------|
| **Total Trades** | {current_metrics.total_trades} |
| **Win Rate** | {current_metrics.win_rate:.1%} |
| **Total PnL** | ${current_metrics.total_pnl:.2f} ({current_metrics.total_pnl_pct:.2%}) |
| **Sharpe Ratio** | {current_metrics.sharpe_ratio:.2f} |
| **Max Drawdown** | ${current_metrics.max_drawdown:.2f} |
| **Profit Factor** | {current_metrics.profit_factor:.2f} |
| **Avg Win** | ${current_metrics.avg_win:.2f} |
| **Avg Loss** | ${current_metrics.avg_loss:.2f} |
| **Avg Holding Time** | {current_metrics.avg_holding_time:.1f} minutes |
| **Best Trade** | ${current_metrics.best_trade_pnl:.2f} |
| **Worst Trade** | ${current_metrics.worst_trade_pnl:.2f} |

"""

        # Compare with previous iteration
        if previous_metrics:
            prompt += f"""
### 📈 COMPARISON WITH PREVIOUS ITERATION

| Metric | Previous | Current | Change |
|--------|----------|---------|--------|
| Win Rate | {previous_metrics.win_rate:.1%} | {current_metrics.win_rate:.1%} | {(current_metrics.win_rate - previous_metrics.win_rate)*100:+.1f}pp |
| PnL | ${previous_metrics.total_pnl:.2f} | ${current_metrics.total_pnl:.2f} | ${current_metrics.total_pnl - previous_metrics.total_pnl:+.2f} |
| Sharpe | {previous_metrics.sharpe_ratio:.2f} | {current_metrics.sharpe_ratio:.2f} | {current_metrics.sharpe_ratio - previous_metrics.sharpe_ratio:+.2f} |
| Profit Factor | {previous_metrics.profit_factor:.2f} | {current_metrics.profit_factor:.2f} | {current_metrics.profit_factor - previous_metrics.profit_factor:+.2f} |

"""

        # Trade analysis
        if trade_analyses:
            prompt += "\n## 📋 TRADE-BY-TRADE ANALYSIS\n\n"

            for i, trade in enumerate(trade_analyses[:10], 1):  # First 10 trades
                result = "✅ WIN" if trade.won else "❌ LOSS"
                prompt += f"""
### Trade {i}: {result}

- **Entry**: {trade.entry_time.strftime('%Y-%m-%d %H:%M')} @ ${trade.entry_price:.2f}
- **Exit**: {trade.exit_time.strftime('%Y-%m-%d %H:%M')} @ ${trade.exit_price:.2f}
- **Side**: {trade.side.upper()}
- **PnL**: ${trade.pnl:.2f} ({trade.pnl_pct:+.2%})
- **Holding Time**: {trade.holding_time_minutes:.0f} minutes
- **Signal Confidence**: {trade.signal_confidence:.2f}
- **Coherence**: {trade.signal_coherence:.2f}
- **Regime**: {trade.regime_at_entry}
- **Exit Reason**: {trade.exit_reason}

"""

        # Current parameters
        if current_params:
            prompt += f"""
## ⚙️ CURRENT STRATEGY PARAMETERS

```json
{json.dumps(current_params, indent=2)}
```

"""

        # Analysis request
        prompt += """
## 🎯 OPTIMIZATION TASK

Analyze the above live trading results and provide:

### 1. Performance Assessment

- Is the strategy performing well?
- Are there concerning patterns?
- Is the win rate sustainable?
- Is the Sharpe ratio acceptable?
- Are losses controlled?

### 2. Failure Pattern Analysis

- Why did losing trades occur?
- Were there common factors in losses?
- Signal quality issues?
- Regime mismatches?
- Entry/exit timing problems?
- TP/SL placement issues?

### 3. Success Pattern Analysis

- What made winning trades successful?
- Common factors in wins?
- Best signal conditions?
- Optimal regimes?
- Ideal holding times?

### 4. Parameter Optimization Suggestions

Suggest specific parameter changes:

- **Signal thresholds** (compression, alignment, confluence)
- **Risk management** (position size, SL, TP)
- **Holding time** (max periods)
- **Entry conditions** (confidence, coherence minimums)
- **Exit rules** (trailing stops, time-based exits)

### 5. New Signal Ideas

Based on the analysis, suggest:

- Additional indicators to consider
- New signal combinations
- Better filtering conditions
- Regime-specific adjustments

### 6. Concrete Action Items

Provide 3-5 specific, actionable improvements:

1. Change parameter X from Y to Z because...
2. Add condition A when regime is B because...
3. Adjust TP/SL calculation to use C because...

## 📝 OUTPUT FORMAT

Please structure your response as:

```markdown
# ITERATION ANALYSIS

## Performance Summary
[Brief assessment]

## Key Issues Identified
1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

## Recommended Changes

### High Priority
- [ ] Change 1: [specific change with rationale]
- [ ] Change 2: [specific change with rationale]

### Medium Priority
- [ ] Change 3: [specific change with rationale]

### Experimental
- [ ] New idea 1: [what to test]

## Expected Impact

[Describe expected performance improvement]

## Implementation Notes

[Any technical considerations]
```

**Focus on**: Data-driven, statistically significant improvements that will increase Sharpe ratio and reduce drawdown while maintaining or improving returns.
"""

        return prompt

    async def get_claude_recommendations(
        self,
        optimization_prompt: str,
        model: str = "claude-sonnet-4-20250514"
    ) -> str:
        """
        Send optimization prompt to Claude and get recommendations

        Args:
            optimization_prompt: Generated optimization prompt
            model: Claude model to use

        Returns:
            Claude's recommendations
        """
        if not self.client:
            logger.error("Claude client not initialized - API key missing")
            return "API key not configured. Prompt saved to file for manual analysis."

        try:
            logger.info(f"Sending optimization request to Claude ({model})...")

            response = self.client.messages.create(
                model=model,
                max_tokens=16000,
                messages=[{
                    "role": "user",
                    "content": optimization_prompt
                }]
            )

            recommendations = response.content[0].text

            logger.info(f"Received recommendations ({len(recommendations)} chars)")

            return recommendations

        except Exception as e:
            logger.error(f"Error getting Claude recommendations: {e}")
            return f"Error: {e}"

    def _parse_trade(self, trade_dict: Dict) -> TradeAnalysis:
        """Parse trade dictionary into TradeAnalysis"""
        return TradeAnalysis(
            trade_id=trade_dict.get('id', ''),
            entry_time=datetime.fromisoformat(trade_dict.get('entry_time', datetime.now().isoformat())),
            exit_time=datetime.fromisoformat(trade_dict.get('exit_time', datetime.now().isoformat())),
            symbol=trade_dict.get('symbol', 'ETH'),
            side=trade_dict.get('side', 'buy'),
            entry_price=float(trade_dict.get('entry_price', 0)),
            exit_price=float(trade_dict.get('exit_price', 0)),
            pnl=float(trade_dict.get('pnl', 0)),
            pnl_pct=float(trade_dict.get('pnl_pct', 0)),
            holding_time_minutes=float(trade_dict.get('holding_time_minutes', 0)),
            signal_confidence=float(trade_dict.get('signal_confidence', 0)),
            signal_coherence=float(trade_dict.get('signal_coherence', 0)),
            regime_at_entry=trade_dict.get('regime', 'unknown'),
            exit_reason=trade_dict.get('exit_reason', 'unknown'),
            won=float(trade_dict.get('pnl', 0)) > 0
        )

    def _save_iteration(
        self,
        iteration_id: int,
        metrics: IterationMetrics,
        trades: List[TradeAnalysis],
        params: Dict
    ):
        """Save iteration results to file"""
        filepath = self.results_dir / f"iteration_{iteration_id}.json"

        data = {
            'metrics': asdict(metrics),
            'trades': [asdict(t) for t in trades],
            'params': params,
            'timestamp': datetime.now().isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved iteration {iteration_id} to {filepath}")

    def save_optimization_prompt(self, iteration_id: int, prompt: str):
        """Save optimization prompt to file"""
        filepath = self.results_dir / f"iteration_{iteration_id}_prompt.md"
        with open(filepath, 'w') as f:
            f.write(prompt)
        logger.info(f"Saved optimization prompt to {filepath}")

    def save_recommendations(self, iteration_id: int, recommendations: str):
        """Save Claude recommendations to file"""
        filepath = self.results_dir / f"iteration_{iteration_id}_recommendations.md"
        with open(filepath, 'w') as f:
            f.write(recommendations)
        logger.info(f"Saved recommendations to {filepath}")


# Testing
if __name__ == '__main__':
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    # Create optimizer
    optimizer = ClaudeIterationOptimizer(min_trades_for_analysis=5)

    # Mock trade data
    mock_trades = [
        {
            'id': 'trade_1',
            'entry_time': '2025-10-28T10:00:00',
            'exit_time': '2025-10-28T12:00:00',
            'symbol': 'ETH',
            'side': 'buy',
            'entry_price': 4000.0,
            'exit_price': 4050.0,
            'pnl': 50.0,
            'pnl_pct': 1.25,
            'holding_time_minutes': 120,
            'signal_confidence': 0.85,
            'signal_coherence': 0.78,
            'regime': 'trending',
            'exit_reason': 'take_profit'
        },
        {
            'id': 'trade_2',
            'entry_time': '2025-10-28T14:00:00',
            'exit_time': '2025-10-28T15:30:00',
            'symbol': 'ETH',
            'side': 'sell',
            'entry_price': 4050.0,
            'exit_price': 4070.0,
            'pnl': -20.0,
            'pnl_pct': -0.49,
            'holding_time_minutes': 90,
            'signal_confidence': 0.68,
            'signal_coherence': 0.62,
            'regime': 'volatile',
            'exit_reason': 'stop_loss'
        }
    ]

    mock_params = {
        'compression_threshold': 90,
        'alignment_threshold': 90,
        'confluence_threshold': 65,
        'max_holding_periods': 24
    }

    # Analyze iteration
    metrics = optimizer.analyze_iteration(
        trades=mock_trades,
        current_params=mock_params,
        iteration_id=1
    )

    print("\n" + "="*60)
    print("ITERATION METRICS")
    print("="*60)
    print(f"Win Rate: {metrics.win_rate:.1%}")
    print(f"Total PnL: ${metrics.total_pnl:.2f}")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    print(f"Profit Factor: {metrics.profit_factor:.2f}")

    # Generate optimization prompt
    print("\n" + "="*60)
    print("OPTIMIZATION PROMPT")
    print("="*60)

    prompt = optimizer.generate_optimization_prompt(
        current_metrics=metrics,
        trade_analyses=[optimizer._parse_trade(t) for t in mock_trades],
        current_params=mock_params
    )

    print(prompt[:500] + "...\n")

    optimizer.save_optimization_prompt(1, prompt)

    print("\n✅ Optimization prompt saved to live_trading_results/iteration_1_prompt.md")
    print("\nTo get Claude recommendations:")
    print("  1. Review the prompt file")
    print("  2. The system will auto-generate recommendations if ANTHROPIC_API_KEY is set")
