# REQUIRED FILES TO RUN run_dual_bot_optimized.py

## MINIMUM REQUIRED FILES (20 Python Files)

### Core Bot Files (4 files)
```
run_dual_bot_optimized.py          # Main entry point
dual_timeframe_bot_with_optimizer.py  # Bot with auto-optimization
dual_timeframe_bot.py              # Core trading bot logic
rule_based_trader.py               # FREE rule-based trading (no API calls)
```

### Trading Logic & Analysis (7 files)
```
claude_trader.py                   # Fallback API-based trader
continuous_learning.py             # Auto-learning system
ema_derivative_analyzer.py         # EMA derivative analysis
big_movement_ema_analyzer.py       # Big movement detection
actual_trade_learner.py            # Learns from actual trades
optimal_vs_actual_analyzer.py      # Compares optimal vs actual trades
smart_trade_finder.py              # Realistic backtest finder
```

### Optimization & Rules (4 files)
```
rule_optimizer.py                  # Automatic rule optimization
rule_version_manager.py            # Rule versioning system
initialize_trading_rules.py        # Initial rule setup
optimal_trade_finder_30min.py      # Finds optimal trades
```

### History & Notifications (3 files)
```
training_history.py                # Training data management
telegram_notifier.py               # Telegram notifications
ultimate_backtest_analyzer.py      # Comprehensive backtest analysis
```

### Support Files (2 files)
```
.env                               # Environment variables
requirements.txt                   # Python dependencies
```

---

## CONFIGURATION FILES (2 files)

### Required JSON Files
```
trading_rules.json                 # Current trading rules (REQUIRED)
trading_rules_phase1.json          # Enhanced Phase 1 rules (optional)
```

**Note**: If `trading_rules.json` doesn't exist, the bot will create it on first run.

---

## DATA DIRECTORIES (2 directories)

### trading_data/ (created automatically)
```
trading_data/
├── ema_data_5min.csv              # 5-minute EMA data (auto-generated)
├── ema_data_15min.csv             # 15-minute EMA data (auto-generated)
├── claude_decisions.csv           # Trading decisions log (auto-generated)
├── optimal_trades.json            # Optimal trade analysis (auto-generated)
├── optimal_trades_last_30min.json # Recent optimal trades (auto-generated)
├── backtest_trades.json           # Backtest results (auto-generated)
└── big_movement_analysis.json     # Big movement analysis (auto-generated)
```

### rule_versions/ (created automatically)
```
rule_versions/
└── v*.json                        # Historical rule versions (auto-generated)
```

---

## EXTERNAL DEPENDENCIES (installed via pip)

### Required Python Packages
```
anthropic                          # Claude API client
python-dotenv                      # Environment variable loading
pandas                             # Data analysis
numpy                              # Numerical computing
requests                           # HTTP requests
eth-account                        # Ethereum wallet
hyperliquid-python-sdk             # Hyperliquid exchange API
selenium                           # Web scraping (for data collection)
```

**Install with**: `pip install -r requirements.txt`

---

## FILES YOU CAN DELETE (Everything Else)

### Utility Scripts (in utils/)
```
utils/backtest_current_rules.py    # Testing tool - not needed to run
utils/backtest_phase1.py            # Testing tool - not needed to run
utils/backtest_phase1_simple.py     # Testing tool - not needed to run
utils/find_optimal_trades.py        # Analysis tool - not needed to run
utils/visualize_trading_analysis.py # Visualization - not needed to run
utils/test_optimization_telegram.py # Testing tool - not needed to run
```

### Documentation (in docs/)
```
All 31 .md files in docs/ are documentation only
```

### Archive (in archive/)
```
Everything in archive/ is old/backup files
```

### Other Files in Root (NOT NEEDED)
```
analyze_ema_derivatives.py         # Analysis tool only
backtest_ema_strategy.py           # Testing tool only
ema_pattern_finder.py              # Research tool only
fix_dependencies.py                # One-time fix script
test_cost_optimization.py          # Testing only
test_derivative_integration.py     # Testing only
cleanup_project.sh                 # Cleanup script (already ran)
README.md                          # Documentation
training_insights.json             # Generated data (can recreate)
training_history.json              # Generated data (can recreate)
trading_rules_EXPANDED.json        # Old rules version
```

### Backup Directories
```
backup_before_cleanup_*/           # All backup folders can be deleted
```

---

## SUMMARY: ABSOLUTE MINIMUM TO RUN

### Python Files (20)
1. run_dual_bot_optimized.py
2. dual_timeframe_bot_with_optimizer.py
3. dual_timeframe_bot.py
4. rule_based_trader.py
5. claude_trader.py
6. continuous_learning.py
7. ema_derivative_analyzer.py
8. big_movement_ema_analyzer.py
9. actual_trade_learner.py
10. optimal_vs_actual_analyzer.py
11. smart_trade_finder.py
12. rule_optimizer.py
13. rule_version_manager.py
14. initialize_trading_rules.py
15. optimal_trade_finder_30min.py
16. training_history.py
17. telegram_notifier.py
18. ultimate_backtest_analyzer.py
19. .env
20. requirements.txt

### Config Files (1-2)
- trading_rules.json (auto-created if missing)
- trading_rules_phase1.json (optional - for Phase 1 deployment)

### Directories (2 - auto-created)
- trading_data/ (auto-created)
- rule_versions/ (auto-created)

---

## TO CLEAN UP FURTHER

If you want an even cleaner folder, you can safely **DELETE**:

1. **All of utils/** - These are testing/analysis tools
2. **All of docs/** - These are documentation files
3. **All of archive/** - These are old files
4. **All backup_before_cleanup_*/** directories
5. **These root files**:
   - analyze_ema_derivatives.py
   - backtest_ema_strategy.py
   - ema_pattern_finder.py
   - fix_dependencies.py
   - test_cost_optimization.py
   - test_derivative_integration.py
   - cleanup_project.sh
   - training_insights.json
   - training_history.json
   - trading_rules_EXPANDED.json
   - README.md (if you don't need it)

**After cleanup, you'll have exactly 20 Python files + .env + requirements.txt in your root directory.**

---

## VERIFICATION

To verify you have everything needed, run:
```bash
python3 run_dual_bot_optimized.py --help
```

If it runs without import errors, you have all required files!
