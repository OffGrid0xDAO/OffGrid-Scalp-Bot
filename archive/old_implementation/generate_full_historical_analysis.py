#!/usr/bin/env python3
"""
Generate Full Historical Analysis
Runs on first optimization to analyze ALL available data:
1. Find optimal trades from entire history
2. Backtest current rules on entire history  
3. Generate trading_analysis.html with visualizations
4. Prepare data for Telegram message

This gives the optimizer a complete view of performance on ALL data.
"""

import os
import sys
import json
from datetime import datetime
from smart_trade_finder import SmartTradeFinder
from visualize_trading_analysis import TradingVisualizer


def generate_full_analysis():
    """Generate comprehensive analysis of all historical data"""
    
    print("\n" + "="*70)
    print("📊 GENERATING FULL HISTORICAL ANALYSIS")
    print("="*70)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis analyzes ALL available historical data...")
    print("="*70 + "\n")
    
    # Check if EMA data exists
    ema_5min_path = 'trading_data/ema_data_5min.csv'
    if not os.path.exists(ema_5min_path):
        print(f"❌ EMA data not found: {ema_5min_path}")
        print("   Cannot generate analysis without historical data")
        return False
    
    file_size_mb = os.path.getsize(ema_5min_path) / (1024 * 1024)
    print(f"📁 Found {file_size_mb:.1f}MB of historical EMA data\n")
    
    # Step 1: Find optimal trades from ALL history
    print("[1/3] 🎯 Finding optimal trades from ENTIRE history...")
    try:
        finder = SmartTradeFinder(
            ema_5min_path='trading_data/ema_data_5min.csv',
            ema_15min_path='trading_data/ema_data_15min.csv'
        )
        
        results = finder.find_all_optimal_trades()
        
        # Save to optimal_trades.json (full history)
        with open('trading_data/optimal_trades.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        total_trades = results.get('total_trades', 0)
        total_pnl = results.get('total_pnl_pct', 0)
        print(f"   ✅ Found {total_trades} optimal trades")
        print(f"   💰 Total PnL: {total_pnl:+.2f}%")
        
    except Exception as e:
        print(f"   ⚠️  Failed to generate optimal trades: {e}")
        print("   Continuing with existing data...")
    
    # Step 2: Backtest current rules on ALL history
    print("\n[2/3] 🧪 Backtesting current rules on ENTIRE history...")
    try:
        # Import and run Phase 1 backtest
        from backtest_phase1_rules import backtest_phase1_rules
        
        backtest_results = backtest_phase1_rules(
            ema_5min_path='trading_data/ema_data_5min.csv',
            output_path='trading_data/backtest_trades.json'
        )
        
        total_trades = backtest_results.get('total_trades', 0)
        total_pnl = backtest_results.get('total_pnl_pct', 0)
        win_rate = backtest_results.get('win_rate', 0)
        
        print(f"   ✅ Simulated {total_trades} trades")
        print(f"   💰 Total PnL: {total_pnl:+.2f}%")
        print(f"   📊 Win Rate: {win_rate:.1f}%")
        
    except ImportError:
        print("   ⚠️  Backtest script not available")
        print("   Continuing without backtest data...")
    except Exception as e:
        print(f"   ⚠️  Backtest failed: {e}")
        print("   Continuing without backtest data...")
    
    # Step 3: Generate interactive HTML visualization
    print("\n[3/3] 📊 Generating trading_analysis.html...")
    try:
        visualizer = TradingVisualizer(
            ema_data_file='trading_data/ema_data_5min.csv',
            decisions_file='trading_data/claude_decisions.csv',
            optimal_trades_file='trading_data/optimal_trades.json',
            backtest_trades_file='trading_data/backtest_trades.json'
        )
        
        # Load data
        if visualizer.load_data():
            # Create visualization (last 24 hours by default)
            html_path = visualizer.create_visualization(
                output_file='trading_data/trading_analysis.html',
                lookback_hours=24
            )
            
            if html_path and os.path.exists(html_path):
                file_size_kb = os.path.getsize(html_path) / 1024
                print(f"   ✅ Generated {html_path} ({file_size_kb:.0f}KB)")
                print(f"   📂 Open in browser: file://{os.path.abspath(html_path)}")
            else:
                print("   ⚠️  HTML file not generated")
        else:
            print("   ⚠️  Could not load data for visualization")
            
    except Exception as e:
        print(f"   ⚠️  Visualization failed: {e}")
        import traceback
        traceback.print_exc()
        print("   Continuing without HTML visualization...")
    
    print("\n" + "="*70)
    print("✅ FULL HISTORICAL ANALYSIS COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    print("  • trading_data/optimal_trades.json - All optimal trades")
    print("  • trading_data/backtest_trades.json - All backtest trades")  
    print("  • trading_data/trading_analysis.html - Interactive visualization")
    print("\n💡 These files will be used by the optimizer for the 3-way comparison")
    print("="*70 + "\n")
    
    return True


if __name__ == '__main__':
    success = generate_full_analysis()
    sys.exit(0 if success else 1)
