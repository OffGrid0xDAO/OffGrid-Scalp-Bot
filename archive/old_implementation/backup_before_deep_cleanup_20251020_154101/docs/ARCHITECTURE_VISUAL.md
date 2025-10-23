# Trading Bot Architecture - Visual Guide

## Entry Point & Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  👤 YOU RUN:  python3 run_dual_bot_optimized.py               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  run_dual_bot_optimized.py                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • Loads .env configuration                                    │
│  • Checks if first-time setup needed                           │
│  • Starts DualTimeframeBotWithOptimizer                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  dual_timeframe_bot_with_optimizer.py                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • Inherits from DualTimeframeBot                              │
│  • Adds RuleOptimizer                                          │
│  • Runs optimization every 30 minutes                          │
│  • Coordinates trading + optimization                          │
└─────────────────────────────────────────────────────────────────┘
                    │                        │
                    │                        │
    ┌───────────────┘                        └───────────────┐
    │                                                        │
    ▼                                                        ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│  dual_timeframe_bot.py          │    │  rule_optimizer.py              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │    │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  MAIN TRADING ENGINE             │    │  OPTIMIZATION ENGINE             │
│                                  │    │                                  │
│  • Monitors 5min & 15min data   │    │  • Runs every 30 minutes        │
│  • Uses rule_based_trader       │    │  • Finds optimal trades         │
│  • Executes trades              │    │  • Analyzes big movements       │
│  • Manages positions            │    │  • Calls Claude for insights    │
│  • Sends Telegram updates       │    │  • Updates trading_rules.json   │
│  • Continuous operation         │    │  • Sends Telegram summary       │
└──────────────────────────────────┘    └──────────────────────────────────┘
    │                                                │
    │                                                │
    ▼                                                ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│  rule_based_trader.py           │    │  optimal_trade_finder_30min.py  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │    │  big_movement_ema_analyzer.py   │
│  • Reads trading_rules.json     │    │  rule_version_manager.py        │
│  • Makes entry/exit decisions   │    │  telegram_notifier.py           │
│  • NO API calls (fast & free)   │    │                                  │
│  • Returns trade recommendations │    │                                  │
└──────────────────────────────────┘    └──────────────────────────────────┘
```

---

## Data Flow

```
┌─────────────────┐
│  Exchange API   │ ← Bot fetches price & EMA data
└─────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  trading_data/ema_data_5min.csv  &  ema_data_15min.csv         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • Stores all EMA calculations                                  │
│  • Ribbon states (all_green, all_red, etc.)                     │
│  • Price data                                                    │
│  • Updated continuously                                          │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  rule_based_trader.py reads data                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • Analyzes ribbon state                                        │
│  • Checks entry conditions                                       │
│  • Classifies into tiers (1=strong, 2=moderate)                 │
│  • Returns decision: ENTER, EXIT, or HOLD                       │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  trading_data/claude_decisions.csv                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • Logs every decision                                          │
│  • Entry/exit times                                             │
│  • PnL, confidence, reasoning                                   │
│  • Used for analysis & learning                                 │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Every 30 minutes: rule_optimizer.py analyzes                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • Reads EMA data                                               │
│  • Finds optimal trades (perfect hindsight)                     │
│  • Compares with actual trades                                  │
│  • Calls Claude API for optimization                            │
│  • Updates trading_rules.json                                   │
│  • Sends Telegram summary                                       │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  trading_rules.json  UPDATED                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  • New optimized rules                                          │
│  • rule_based_trader.py auto-reloads                            │
│  • Bot immediately uses new rules                               │
│  • Continuous improvement!                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Relationships

### Core Trading Loop (Every ~10 seconds)

```
dual_timeframe_bot.py
    ↓ fetch data
ema_data_5min.csv & ema_data_15min.csv
    ↓ analyze
rule_based_trader.py (reads trading_rules.json)
    ↓ decision
ENTER/EXIT/HOLD
    ↓ log
claude_decisions.csv
    ↓ notify
telegram_notifier.py → 📱 Your Phone
```

### Optimization Loop (Every 30 minutes)

```
rule_optimizer.py (triggered by dual_timeframe_bot_with_optimizer.py)
    ↓ analyze
ema_data_5min.csv + claude_decisions.csv
    ↓ find patterns
optimal_trade_finder_30min.py
big_movement_ema_analyzer.py
    ↓ call AI
Claude API (Anthropic)
    ↓ receive insights
recommendations JSON
    ↓ apply
trading_rules.json UPDATED
    ↓ notify
telegram_notifier.py → 📱 Your Phone (optimization summary)
```

---

## Core Files by Layer

### Layer 1: Entry & Control (3 files)
```
run_dual_bot_optimized.py
    └── dual_timeframe_bot_with_optimizer.py
            └── initialize_trading_rules.py (first-time only)
```

### Layer 2: Trading Engine (4 files)
```
dual_timeframe_bot.py
    ├── rule_based_trader.py          (decision maker)
    ├── ema_derivative_analyzer.py    (technical analysis)
    ├── claude_trader.py              (API wrapper - backup)
    └── telegram_notifier.py          (notifications)
```

### Layer 3: Optimization Engine (4 files)
```
rule_optimizer.py
    ├── optimal_trade_finder_30min.py    (find optimal trades)
    ├── big_movement_ema_analyzer.py     (analyze big moves)
    ├── rule_version_manager.py          (version control)
    └── telegram_notifier.py             (send updates)
```

### Layer 4: Learning System (6 files)
```
continuous_learning.py
    ├── actual_trade_learner.py          (learn from actual trades)
    ├── optimal_vs_actual_analyzer.py    (gap analysis)
    ├── smart_trade_finder.py            (realistic backtest)
    ├── training_history.py              (history tracking)
    └── ultimate_backtest_analyzer.py    (advanced analysis)
```

---

## Decision Flow

```
                    ┌─────────────────────┐
                    │  Market Data        │
                    │  (Price + EMAs)     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  rule_based_trader  │
                    │  reads rules.json   │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
         ┌──────────┐   ┌──────────┐   ┌──────────┐
         │ NO       │   │ IN       │   │ CHECK    │
         │ POSITION │   │ POSITION │   │ ENTRY    │
         └────┬─────┘   └────┬─────┘   └──────────┘
              │              │
              ▼              ▼
    ┌──────────────┐  ┌──────────────┐
    │ Check Entry  │  │ Check Exit   │
    │ Conditions   │  │ Conditions   │
    └──────┬───────┘  └──────┬───────┘
           │                 │
           ▼                 ▼
    ┌──────────────────────────────────┐
    │     Classify into Tier           │
    │  • Tier 1: Strong Trend          │
    │    (all_green/all_red, 11+ EMAs) │
    │  • Tier 2: Moderate Trend        │
    │    (strong_green, 8+ EMAs)       │
    └──────┬───────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │  Apply Tier-Specific Rules       │
    │  • Tier 1: Hold 15+ min          │
    │    Exit only on strong reversal  │
    │  • Tier 2: Hold 8+ min           │
    │    Exit on any opposite state    │
    └──────┬───────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │        Return Decision            │
    │  • ENTER (with tier)              │
    │  • EXIT (with reason)             │
    │  • HOLD (with status)             │
    └───────────────────────────────────┘
```

---

## Phase 1 Enhancement Architecture

### Before (Original):
```
Entry: any ribbon state → Enter
Hold: 3.5 min average
Exit: ANY ribbon flip → Exit immediately
Result: -0.14% PnL, too short holds
```

### After (Phase 1):
```
Entry: Classified into tiers
  Tier 1: all_green/all_red + 11+ light EMAs + 5min stability
  Tier 2: strong_green/strong_red + 8+ light EMAs + 3min stability

Hold: Tier-specific minimum
  Tier 1: 15 minutes minimum
  Tier 2: 8 minutes minimum

Exit: Tier-specific logic
  Tier 1: Only on OPPOSITE STRONG STATE (all_green → all_red)
  Tier 2: On any opposite state

Result: +2.61% PnL, 38min average holds (10.9x improvement!)
```

---

## Folder Organization

### Current (Flat):
```
TradingScalper/
├── run_dual_bot_optimized.py
├── [50+ other files mixed together]
├── trading_data/
└── rule_versions/
```

### Proposed (Organized):
```
TradingScalper/
├── run_dual_bot_optimized.py          ⭐ Entry point
├── .env                               🔐 Config
├── trading_rules.json                 📋 Current rules
│
├── [20 core .py files]                🎯 Core (keep in root)
│
├── utils/                             🛠️ Utilities
│   ├── backtest_current_rules.py
│   ├── backtest_phase1_simple.py
│   ├── find_optimal_trades.py
│   └── visualize_trading_analysis.py
│
├── docs/                              📄 Documentation
│   ├── ARCHITECTURE_AND_CLEANUP.md
│   ├── PHASE1_COMPLETE.md
│   └── [other .md files]
│
├── trading_data/                      📊 Generated data
│   ├── ema_data_5min.csv
│   ├── claude_decisions.csv
│   └── [other data files]
│
├── rule_versions/                     🗄️ Rule history
│   └── rule_version_*.json
│
└── archive/                           🗑️ Old/unused
    ├── scratches/
    └── backups/
```

---

## Quick Reference

### To Run Bot:
```bash
python3 run_dual_bot_optimized.py
```

### To Cleanup Project:
```bash
./cleanup_project.sh
```

### To Backtest Phase 1:
```bash
python3 utils/backtest_phase1_simple.py
```

### To Visualize Trades:
```bash
python3 utils/visualize_trading_analysis.py
```

### To Find Optimal Trades:
```bash
python3 utils/find_optimal_trades.py
```

---

## Summary

**Entry Point**: 1 file (`run_dual_bot_optimized.py`)

**Core Files**: 20 files (required)

**Utility Files**: 7 files (optional, helpful)

**Data Files**: Generated automatically

**Documentation**: 12+ files (reference)

**Total Essential**: ~27 files to run bot + analyze performance

---

**Created**: 2025-10-20
**Purpose**: Visual architecture guide
**Use**: Understand how everything connects
