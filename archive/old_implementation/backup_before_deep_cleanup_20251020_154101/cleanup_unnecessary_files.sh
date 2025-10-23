#!/bin/bash

# Cleanup Unnecessary Files Script
# Removes all files that are NOT needed to run run_dual_bot_optimized.py
# Creates backup before deletion for safety

echo "======================================================================="
echo "🧹 CLEANUP UNNECESSARY FILES"
echo "======================================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "run_dual_bot_optimized.py" ]; then
    echo "❌ Error: Must run from TradingScalper root directory"
    exit 1
fi

echo "✅ Found run_dual_bot_optimized.py"
echo ""

# Create backup
BACKUP_DIR="backup_before_deep_cleanup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp -r . "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup created"
echo ""

# Show what will be deleted
echo "📋 FILES AND FOLDERS TO DELETE:"
echo "─────────────────────────────────────────────────────────────────────"
echo ""
echo "📁 FOLDERS:"
echo "   • utils/ (6 testing/analysis tools)"
echo "   • docs/ (31 documentation files)"
echo "   • archive/ (old files)"
echo "   • backup_before_cleanup_*/ (old backups)"
echo ""
echo "📄 ROOT FILES:"
echo "   • analyze_ema_derivatives.py"
echo "   • backtest_ema_strategy.py"
echo "   • ema_pattern_finder.py"
echo "   • fix_dependencies.py"
echo "   • test_cost_optimization.py"
echo "   • test_derivative_integration.py"
echo "   • cleanup_project.sh"
echo "   • training_insights.json"
echo "   • training_history.json"
echo "   • trading_rules_EXPANDED.json"
echo "   • rule_based_trader_phase1.py (keep if using Phase 1)"
echo "   • trading_rules_phase1.json (keep if using Phase 1)"
echo ""
echo "─────────────────────────────────────────────────────────────────────"
echo ""

# Ask for confirmation
read -p "⚠️  Delete all unnecessary files? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo ""
    echo "❌ Cleanup cancelled"
    echo "   (Backup still created at: $BACKUP_DIR)"
    exit 0
fi

echo ""
echo "🗑️  Deleting unnecessary files..."
echo ""

# Delete folders
if [ -d "utils" ]; then
    rm -rf utils
    echo "  ✓ Deleted utils/"
fi

if [ -d "docs" ]; then
    rm -rf docs
    echo "  ✓ Deleted docs/"
fi

if [ -d "archive" ]; then
    rm -rf archive
    echo "  ✓ Deleted archive/"
fi

# Delete old backup folders (but not the one we just created)
for dir in backup_before_cleanup_*/; do
    if [ -d "$dir" ] && [ "$dir" != "$BACKUP_DIR/" ]; then
        rm -rf "$dir"
        echo "  ✓ Deleted $dir"
    fi
done

# Delete unnecessary root files
FILES_TO_DELETE=(
    "analyze_ema_derivatives.py"
    "backtest_ema_strategy.py"
    "ema_pattern_finder.py"
    "fix_dependencies.py"
    "test_cost_optimization.py"
    "test_derivative_integration.py"
    "cleanup_project.sh"
    "training_insights.json"
    "training_history.json"
    "trading_rules_EXPANDED.json"
)

for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✓ Deleted $file"
    fi
done

echo ""

# Ask about Phase 1 files
echo "──────────────────────────────────────────────────────────────────────"
echo "📊 PHASE 1 FILES (Enhanced trading rules):"
echo ""
echo "   • rule_based_trader_phase1.py"
echo "   • trading_rules_phase1.json"
echo ""
echo "   These contain the Phase 1 enhancements (10.9x hold time improvement)"
echo ""
read -p "   Keep Phase 1 files? (yes/no): " keep_phase1

if [ "$keep_phase1" != "yes" ]; then
    if [ -f "rule_based_trader_phase1.py" ]; then
        rm "rule_based_trader_phase1.py"
        echo "  ✓ Deleted rule_based_trader_phase1.py"
    fi
    if [ -f "trading_rules_phase1.json" ]; then
        rm "trading_rules_phase1.json"
        echo "  ✓ Deleted trading_rules_phase1.json"
    fi
else
    echo "  ✓ Kept Phase 1 files"
fi

echo ""

# Summary
echo "======================================================================="
echo "✅ CLEANUP COMPLETE"
echo "======================================================================="
echo ""
echo "📊 REMAINING FILES (Core Bot Only):"
echo ""

# Count remaining Python files
py_count=$(ls -1 *.py 2>/dev/null | wc -l | tr -d ' ')
json_count=$(ls -1 *.json 2>/dev/null | wc -l | tr -d ' ')

echo "  Python files: $py_count"
echo "  JSON files: $json_count"
echo "  Config: .env, requirements.txt"
echo ""

# List all remaining files in root
echo "📁 ROOT DIRECTORY CONTENTS:"
echo "─────────────────────────────────────────────────────────────────────"
ls -1 *.py *.json .env requirements.txt 2>/dev/null | head -30
echo "─────────────────────────────────────────────────────────────────────"
echo ""

# Test bot
echo "🧪 Testing bot..."
python3 run_dual_bot_optimized.py --help > /dev/null 2>&1 && echo "✅ Bot loads successfully!" || echo "⚠️  Bot may have import issues - check imports"
echo ""

echo "======================================================================="
echo "🎉 PROJECT IS NOW MINIMAL!"
echo ""
echo "📦 Backup saved to: $BACKUP_DIR"
echo ""
echo "To run bot: python3 run_dual_bot_optimized.py"
echo "To rollback: rm -rf *.py *.json && cp -r $BACKUP_DIR/* ."
echo "======================================================================="
echo ""
