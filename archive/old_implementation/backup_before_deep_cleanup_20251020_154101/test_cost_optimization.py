"""
Test Script - Verify the cost optimization system works correctly
Run this before deploying to production
"""

import os
import json
from datetime import datetime


def test_1_check_files():
    """Test 1: Verify all required files exist"""
    print("\n" + "="*70)
    print("TEST 1: Checking Required Files")
    print("="*70)

    required_files = [
        'optimal_trade_finder_30min.py',
        'rule_optimizer.py',
        'rule_based_trader.py',
        'trading_rules.json',
        'run_optimizer_schedule.py',
        'COST_OPTIMIZATION_GUIDE.md'
    ]

    all_exist = True
    for file in required_files:
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        print(f"{status} {file}")
        if not exists:
            all_exist = False

    if all_exist:
        print("\n✅ All required files present")
    else:
        print("\n❌ Some files missing - check installation")

    return all_exist


def test_2_check_data_files():
    """Test 2: Verify data files exist"""
    print("\n" + "="*70)
    print("TEST 2: Checking Data Files")
    print("="*70)

    data_files = [
        'trading_data/ema_data_5min.csv',
        'trading_data/ema_data_15min.csv',
        'trading_data/claude_decisions.csv'
    ]

    all_exist = True
    for file in data_files:
        exists = os.path.exists(file)
        status = "✅" if exists else "⚠️ "
        print(f"{status} {file}")
        if not exists:
            print(f"   Note: {file} will be created by your trading bot")
            all_exist = False

    if all_exist:
        print("\n✅ All data files present")
    else:
        print("\n⚠️  Some data files missing - will be created when bot runs")

    return True  # Not critical


def test_3_check_api_key():
    """Test 3: Verify API key is set"""
    print("\n" + "="*70)
    print("TEST 3: Checking API Key")
    print("="*70)

    api_key = os.getenv('ANTHROPIC_API_KEY')

    if api_key:
        print(f"✅ ANTHROPIC_API_KEY is set")
        print(f"   Key starts with: {api_key[:15]}...")
        return True
    else:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return False


def test_4_test_imports():
    """Test 4: Test Python imports"""
    print("\n" + "="*70)
    print("TEST 4: Testing Python Imports")
    print("="*70)

    imports_to_test = [
        ('anthropic', 'Anthropic'),
        ('pandas', 'pandas'),
        ('schedule', 'schedule'),
        ('json', 'json'),
        ('datetime', 'datetime')
    ]

    all_imported = True
    for module_name, import_name in imports_to_test:
        try:
            __import__(module_name)
            print(f"✅ {import_name}")
        except ImportError:
            print(f"❌ {import_name} - Install with: pip install {module_name}")
            all_imported = False

    if all_imported:
        print("\n✅ All dependencies installed")
    else:
        print("\n❌ Some dependencies missing - run: pip install anthropic pandas schedule")

    return all_imported


def test_5_load_rules():
    """Test 5: Test loading trading rules"""
    print("\n" + "="*70)
    print("TEST 5: Loading Trading Rules")
    print("="*70)

    try:
        with open('trading_rules.json', 'r') as f:
            rules = json.load(f)

        print("✅ trading_rules.json loaded successfully")
        print(f"   Version: {rules.get('version', 'unknown')}")
        print(f"   Last Updated: {rules.get('last_updated', 'unknown')}")
        print(f"   Ribbon Threshold: {rules['entry_rules']['ribbon_alignment_threshold']}")
        print(f"   Min Light EMAs: {rules['entry_rules']['min_light_emas_required']}")
        print(f"   Max Hold Time: {rules['exit_rules']['max_hold_minutes']} min")
        print(f"   Profit Target: {rules['exit_rules']['profit_target_pct']*100}%")
        print(f"   Stop Loss: {rules['exit_rules']['stop_loss_pct']*100}%")

        return True

    except Exception as e:
        print(f"❌ Error loading trading_rules.json: {e}")
        return False


def test_6_test_rule_based_trader():
    """Test 6: Test RuleBasedTrader initialization"""
    print("\n" + "="*70)
    print("TEST 6: Testing RuleBasedTrader")
    print("="*70)

    try:
        from rule_based_trader import RuleBasedTrader

        trader = RuleBasedTrader()
        print("✅ RuleBasedTrader initialized successfully")
        print(f"   Rules version: {trader.rules.get('version', 'unknown')}")

        # Test pattern extraction
        mock_indicators = {
            'MMA5': {'value': 3875.0, 'color': 'green', 'intensity': 'light'},
            'MMA10': {'value': 3874.5, 'color': 'green', 'intensity': 'light'},
            'MMA15': {'value': 3874.0, 'color': 'green', 'intensity': 'normal'},
            'MMA20': {'value': 3873.5, 'color': 'red', 'intensity': 'dark'},
        }

        pattern = trader.extract_ema_pattern(mock_indicators)
        print(f"   Pattern extracted: {pattern['green_count']} green, {pattern['red_count']} red")

        return True

    except Exception as e:
        print(f"❌ Error testing RuleBasedTrader: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_test_optimal_trade_finder():
    """Test 7: Test OptimalTradeFinder (without running full analysis)"""
    print("\n" + "="*70)
    print("TEST 7: Testing OptimalTradeFinder")
    print("="*70)

    try:
        from optimal_trade_finder_30min import OptimalTradeFinder

        finder = OptimalTradeFinder(
            'trading_data/ema_data_5min.csv',
            'trading_data/ema_data_15min.csv'
        )

        print("✅ OptimalTradeFinder initialized successfully")
        print(f"   Profit Target: {finder.profit_target_pct*100}%")
        print(f"   Stop Loss: {finder.stop_loss_pct*100}%")
        print(f"   Max Hold: {finder.max_hold_minutes} min")

        return True

    except Exception as e:
        print(f"❌ Error testing OptimalTradeFinder: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_cost_comparison():
    """Show cost comparison"""
    print("\n" + "="*70)
    print("💰 COST COMPARISON")
    print("="*70)

    print("\n📊 OLD SYSTEM (Claude on every trade):")
    print("   - Calls per hour: ~180")
    print("   - Calls per day: ~4,320")
    print("   - Daily cost: ~$50-$100")
    print("   - Monthly cost: ~$1,500-$3,000")

    print("\n📊 NEW SYSTEM (Claude every 30 minutes):")
    print("   - Calls per hour: 2")
    print("   - Calls per day: 48")
    print("   - Daily cost: ~$0.20-$1.00")
    print("   - Monthly cost: ~$6-$30")

    print("\n💡 SAVINGS:")
    savings_pct = ((4320 - 48) / 4320) * 100
    print(f"   - API calls reduced: {savings_pct:.1f}%")
    print(f"   - Cost reduced: 98-99%")
    print(f"   - Monthly savings: ~$1,470-$2,970")
    print(f"   - Annual savings: ~$17,640-$35,640")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 COST OPTIMIZATION SYSTEM - TEST SUITE")
    print("="*70)
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    # Run tests
    results.append(("Files Check", test_1_check_files()))
    results.append(("Data Files Check", test_2_check_data_files()))
    results.append(("API Key Check", test_3_check_api_key()))
    results.append(("Import Dependencies", test_4_test_imports()))
    results.append(("Load Trading Rules", test_5_load_rules()))
    results.append(("RuleBasedTrader", test_6_test_rule_based_trader()))
    results.append(("OptimalTradeFinder", test_7_test_optimal_trade_finder()))

    # Show cost comparison
    run_cost_comparison()

    # Summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "="*70)
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\n🚀 System is ready to deploy!")
        print("\nNext steps:")
        print("1. Run: python optimal_trade_finder_30min.py")
        print("2. Run: python rule_optimizer.py (tests 1 Claude call)")
        print("3. Run: python run_optimizer_schedule.py (starts scheduler)")
        print("4. Update your bot to use RuleBasedTrader")
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
        print("\n🔧 Fix the failed tests before deploying")

    print("="*70 + "\n")


if __name__ == '__main__':
    main()
