#!/usr/bin/env python3
"""
Claude Candlestick Pattern Analyzer

Uses Claude AI to analyze candlestick patterns with EMA ribbon data
to identify high-probability trading setups and patterns.

Usage:
    python3 claude_candlestick_analyzer.py
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ClaudeCandlestickAnalyzer:
    """
    Use Claude AI to analyze candlestick patterns with EMA ribbon context
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Claude candlestick analyzer

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.total_cost = 0.0

        print(f"🧠 Claude Candlestick Analyzer initialized with model: {model}")

    def load_candlestick_csv(self, csv_path: str, limit: int = 100) -> List[Dict]:
        """
        Load candlestick data from CSV file

        Args:
            csv_path: Path to candlestick CSV file
            limit: Maximum number of recent candles to load

        Returns:
            List of candlestick dictionaries
        """
        candles = []

        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    candles.append(row)

            # Get most recent candles
            if len(candles) > limit:
                candles = candles[-limit:]

            print(f"✅ Loaded {len(candles)} candlesticks from {csv_path}")
            if candles:
                print(f"   Time range: {candles[0]['timestamp']} to {candles[-1]['timestamp']}")

            return candles

        except FileNotFoundError:
            print(f"❌ File not found: {csv_path}")
            return []
        except Exception as e:
            print(f"❌ Error loading CSV: {str(e)}")
            return []

    def format_candlesticks_for_claude(self, candles: List[Dict],
                                        include_all_emas: bool = False) -> str:
        """
        Format candlestick data into a CSV string for Claude

        Args:
            candles: List of candlestick dictionaries
            include_all_emas: If True, include all EMA OHLC data (verbose)

        Returns:
            Formatted CSV string
        """
        if not candles:
            return "No candlestick data available"

        # Basic fields for Claude
        if include_all_emas:
            # Include everything (very long, use sparingly)
            csv_lines = []
            if candles:
                # Use first candle's keys as header
                header = ','.join(candles[0].keys())
                csv_lines.append(header)

                for candle in candles:
                    row = ','.join([str(v) for v in candle.values()])
                    csv_lines.append(row)
        else:
            # Simplified view: price action + ribbon state + close prices of key EMAs
            csv_lines = [
                "timestamp,price_open,price_high,price_low,price_close,ribbon_state_close,"
                "MMA5_close,MMA5_color,MMA10_close,MMA10_color,MMA20_close,MMA20_color,"
                "MMA40_close,MMA40_color,MMA100_close,MMA100_color"
            ]

            for candle in candles:
                row = (
                    f"{candle.get('timestamp', '')},"
                    f"{candle.get('price_open', '')},"
                    f"{candle.get('price_high', '')},"
                    f"{candle.get('price_low', '')},"
                    f"{candle.get('price_close', '')},"
                    f"{candle.get('ribbon_state_close', '')},"
                    f"{candle.get('MMA5_close', '')},{candle.get('MMA5_color', '')},"
                    f"{candle.get('MMA10_close', '')},{candle.get('MMA10_color', '')},"
                    f"{candle.get('MMA20_close', '')},{candle.get('MMA20_color', '')},"
                    f"{candle.get('MMA40_close', '')},{candle.get('MMA40_color', '')},"
                    f"{candle.get('MMA100_close', '')},{candle.get('MMA100_color', '')}"
                )
                csv_lines.append(row)

        return '\n'.join(csv_lines)

    def analyze_patterns(self, candles_5min: List[Dict], candles_15min: List[Dict]) -> Dict:
        """
        Use Claude to analyze candlestick patterns across both timeframes

        Args:
            candles_5min: 5-minute candlesticks
            candles_15min: 15-minute candlesticks

        Returns:
            Analysis results from Claude
        """
        # Format candlestick data
        csv_5min = self.format_candlesticks_for_claude(candles_5min[-50:])  # Last 50 candles
        csv_15min = self.format_candlesticks_for_claude(candles_15min[-30:])  # Last 30 candles

        system_prompt = """You are an expert trading analyst specializing in candlestick pattern recognition and EMA ribbon analysis.

Your task is to analyze candlestick data combined with EMA ribbon information to identify:
1. **Candlestick patterns** (bullish/bearish engulfing, hammers, dojis, etc.)
2. **EMA ribbon patterns** (ribbon flips, compression, expansion)
3. **High-probability setups** combining both price action and ribbon signals
4. **Support/Resistance levels** from EMA reactions
5. **Trend strength** and momentum shifts

**ANALYSIS FRAMEWORK:**

**Candlestick Patterns to Look For:**
- Engulfing patterns (bullish/bearish)
- Hammer/Shooting star (reversal signals)
- Doji (indecision)
- Pin bars (rejection wicks)
- Inside bars (consolidation)

**EMA Ribbon Signals:**
- Ribbon state changes (all_green, all_red, mixed)
- EMA color changes (green→red or red→green flips)
- Price relationship to key EMAs (MMA40, MMA100 as support/resistance)
- Ribbon compression (EMAs bunching) vs expansion (EMAs spreading)

**High-Probability Setups:**
1. **Bullish Engulfing + Ribbon Flip to Green** = Strong buy signal
2. **Hammer at EMA Support (MMA40/100) + Ribbon Green** = Reversal buy
3. **Bearish Engulfing + Ribbon Flip to Red** = Strong sell signal
4. **Shooting Star at EMA Resistance + Ribbon Red** = Reversal sell
5. **Inside Bar Breakout + Ribbon Aligned** = Breakout entry

**Output Format:**
Provide a detailed analysis in JSON format."""

        user_message = f"""Analyze the following candlestick data with EMA ribbon context:

**5-MINUTE TIMEFRAME CANDLESTICKS** (Last 50 candles):
{csv_5min}

**15-MINUTE TIMEFRAME CANDLESTICKS** (Last 30 candles):
{csv_15min}

**ANALYSIS INSTRUCTIONS:**

1. **Identify Recent Patterns**: Look at the last 5-10 candles on each timeframe
2. **EMA Ribbon Analysis**: How is the ribbon behaving? Flipping? Aligned?
3. **Price Action Signals**: Any notable candlestick patterns?
4. **High-Probability Setups**: Any current or forming setups?
5. **Support/Resistance**: Where are key EMAs providing S/R?
6. **Trend Assessment**: What's the current trend strength?

Provide your analysis in this JSON format:

```json
{{
  "current_trend": "BULLISH" | "BEARISH" | "NEUTRAL",
  "trend_strength": "STRONG" | "MODERATE" | "WEAK",
  "5min_analysis": {{
    "ribbon_state": "all_green" | "all_red" | "mixed_green" | "mixed_red" | "mixed",
    "recent_patterns": ["list of candlestick patterns observed"],
    "key_observations": "What's happening on this timeframe",
    "support_levels": ["price levels where EMAs provided support"],
    "resistance_levels": ["price levels where EMAs provided resistance"]
  }},
  "15min_analysis": {{
    "ribbon_state": "all_green" | "all_red" | "mixed_green" | "mixed_red" | "mixed",
    "recent_patterns": ["list of candlestick patterns observed"],
    "key_observations": "What's happening on this timeframe",
    "support_levels": ["price levels"],
    "resistance_levels": ["price levels"]
  }},
  "high_probability_setups": [
    {{
      "setup_type": "Name of setup (e.g., Bullish Engulfing + Ribbon Flip)",
      "timeframe": "5min" | "15min" | "both",
      "direction": "LONG" | "SHORT",
      "confidence": "HIGH" | "MEDIUM" | "LOW",
      "description": "Detailed description of the setup",
      "entry_trigger": "What would trigger entry",
      "invalidation": "What would invalidate this setup"
    }}
  ],
  "overall_assessment": "Comprehensive summary of market state and recommended approach"
}}
```
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": f"{system_prompt}\n\n{user_message}"
                    }
                ]
            )

            # Track cost
            usage = response.usage
            input_tokens = getattr(usage, 'input_tokens', 0)
            output_tokens = getattr(usage, 'output_tokens', 0)
            cost = (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0
            self.total_cost += cost

            print(f"💵 Analysis cost: ${cost:.4f} | Total session: ${self.total_cost:.4f}")

            # Parse response
            response_text = response.content[0].text.strip()

            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            analysis = json.loads(response_text)
            return analysis

        except Exception as e:
            print(f"❌ Claude API error: {str(e)}")
            return {
                "error": str(e),
                "current_trend": "UNKNOWN"
            }

    def print_analysis(self, analysis: Dict):
        """
        Print formatted analysis results

        Args:
            analysis: Analysis dictionary from Claude
        """
        if 'error' in analysis:
            print(f"\n❌ Analysis failed: {analysis['error']}")
            return

        print("\n" + "="*80)
        print("CLAUDE CANDLESTICK PATTERN ANALYSIS")
        print("="*80)

        print(f"\n📊 TREND: {analysis.get('current_trend', 'N/A')} ({analysis.get('trend_strength', 'N/A')})")

        # 5min analysis
        print(f"\n📈 5-MINUTE TIMEFRAME:")
        tf_5min = analysis.get('5min_analysis', {})
        print(f"   Ribbon State: {tf_5min.get('ribbon_state', 'N/A')}")
        print(f"   Patterns: {', '.join(tf_5min.get('recent_patterns', []))}")
        print(f"   Observations: {tf_5min.get('key_observations', 'N/A')}")
        if tf_5min.get('support_levels'):
            print(f"   Support Levels: {', '.join(tf_5min.get('support_levels', []))}")
        if tf_5min.get('resistance_levels'):
            print(f"   Resistance Levels: {', '.join(tf_5min.get('resistance_levels', []))}")

        # 15min analysis
        print(f"\n📈 15-MINUTE TIMEFRAME:")
        tf_15min = analysis.get('15min_analysis', {})
        print(f"   Ribbon State: {tf_15min.get('ribbon_state', 'N/A')}")
        print(f"   Patterns: {', '.join(tf_15min.get('recent_patterns', []))}")
        print(f"   Observations: {tf_15min.get('key_observations', 'N/A')}")
        if tf_15min.get('support_levels'):
            print(f"   Support Levels: {', '.join(tf_15min.get('support_levels', []))}")
        if tf_15min.get('resistance_levels'):
            print(f"   Resistance Levels: {', '.join(tf_15min.get('resistance_levels', []))}")

        # High-probability setups
        setups = analysis.get('high_probability_setups', [])
        if setups:
            print(f"\n🎯 HIGH-PROBABILITY SETUPS ({len(setups)} found):")
            for i, setup in enumerate(setups, 1):
                print(f"\n   Setup {i}: {setup.get('setup_type', 'N/A')}")
                print(f"   Timeframe: {setup.get('timeframe', 'N/A')}")
                print(f"   Direction: {setup.get('direction', 'N/A')}")
                print(f"   Confidence: {setup.get('confidence', 'N/A')}")
                print(f"   Description: {setup.get('description', 'N/A')}")
                print(f"   Entry Trigger: {setup.get('entry_trigger', 'N/A')}")
                print(f"   Invalidation: {setup.get('invalidation', 'N/A')}")
        else:
            print(f"\n🎯 HIGH-PROBABILITY SETUPS: None found")

        # Overall assessment
        print(f"\n💡 OVERALL ASSESSMENT:")
        print(f"   {analysis.get('overall_assessment', 'N/A')}")

        print("\n" + "="*80)

    def save_analysis(self, analysis: Dict, output_file: str = 'candlestick_analysis.json'):
        """
        Save analysis to JSON file

        Args:
            analysis: Analysis dictionary
            output_file: Output filename
        """
        analysis['timestamp'] = datetime.now().isoformat()
        analysis['total_cost'] = self.total_cost

        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(f"\n💾 Analysis saved to {output_file}")


def main():
    """Main execution"""
    print("🚀 Claude Candlestick Pattern Analyzer")
    print("="*80)

    # Initialize analyzer
    analyzer = ClaudeCandlestickAnalyzer()

    # Load candlestick data
    candles_5min = analyzer.load_candlestick_csv('candlesticks_5min.csv', limit=100)
    candles_15min = analyzer.load_candlestick_csv('candlesticks_15min.csv', limit=100)

    if not candles_5min or not candles_15min:
        print("\n❌ Could not load candlestick data. Run backtest first to generate CSVs.")
        return

    # Analyze patterns
    print("\n🔍 Analyzing candlestick patterns with Claude AI...")
    analysis = analyzer.analyze_patterns(candles_5min, candles_15min)

    # Print results
    analyzer.print_analysis(analysis)

    # Save to file
    analyzer.save_analysis(analysis)

    print(f"\n✅ Analysis complete! Total cost: ${analyzer.total_cost:.4f}")


if __name__ == "__main__":
    main()
