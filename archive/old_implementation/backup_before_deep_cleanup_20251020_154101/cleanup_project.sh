#!/bin/bash

# Trading Bot Project Cleanup Script
# Organizes files into clean folder structure
# Safe: Creates backups before moving anything

echo "======================================================================="
echo "🧹 TRADING BOT PROJECT CLEANUP"
echo "======================================================================="
echo ""

# Check if we're in the right directory
if [ ! -f "run_dual_bot_optimized.py" ]; then
    echo "❌ Error: Must run from TradingScalper root directory"
    echo "   (Directory with run_dual_bot_optimized.py)"
    exit 1
fi

echo "✅ Found run_dual_bot_optimized.py"
echo ""

# Create backup
BACKUP_DIR="backup_before_cleanup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp -r . "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup created"
echo ""

# Create new directories
echo "📁 Creating folder structure..."
mkdir -p utils
mkdir -p docs
mkdir -p archive
echo "✅ Folders created: utils/, docs/, archive/"
echo ""

# Move utility scripts
echo "🛠️  Moving utility scripts to utils/..."
UTILS=(
    "backtest_current_rules.py"
    "backtest_phase1.py"
    "backtest_phase1_simple.py"
    "find_optimal_trades.py"
    "visualize_trading_analysis.py"
    "test_optimization_telegram.py"
)

for file in "${UTILS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" utils/
        echo "  ✓ Moved $file"
    fi
done
echo ""

# Move documentation
echo "📄 Moving documentation to docs/..."
# Move all .md files except README
for file in *.md; do
    if [ -f "$file" ] && [ "$file" != "README.md" ]; then
        mv "$file" docs/
        echo "  ✓ Moved $file"
    fi
done
echo ""

# Archive old files
echo "🗑️  Archiving old files..."

# Archive scratches directory
if [ -d "scratches" ]; then
    mv scratches archive/
    echo "  ✓ Archived scratches/"
fi

# Archive backup files
for file in trading_rules_backup_*.json; do
    if [ -f "$file" ]; then
        mv "$file" archive/
        echo "  ✓ Archived $file"
    fi
done

# Archive any *_old.py files
for file in *_old.py; do
    if [ -f "$file" ]; then
        mv "$file" archive/
        echo "  ✓ Archived $file"
    fi
done

echo ""

# Summary
echo "======================================================================="
echo "✅ CLEANUP COMPLETE"
echo "======================================================================="
echo ""
echo "📊 New Structure:"
echo "  ├── run_dual_bot_optimized.py  (Entry point)"
echo "  ├── [Core files remain in root]"
echo "  ├── utils/                     (Utility scripts)"
echo "  ├── docs/                      (Documentation)"
echo "  ├── archive/                   (Old files)"
echo "  ├── trading_data/              (Generated data)"
echo "  └── rule_versions/             (Rule history)"
echo ""
echo "📦 Backup saved to: $BACKUP_DIR"
echo ""
echo "🧪 Testing bot..."
python3 run_dual_bot_optimized.py --help > /dev/null 2>&1 && echo "✅ Bot loads successfully!" || echo "⚠️  Bot may have import issues - check imports"
echo ""
echo "======================================================================="
echo "🎉 Project is now organized!"
echo ""
echo "To run bot: python3 run_dual_bot_optimized.py"
echo "To view architecture: cat docs/ARCHITECTURE_AND_CLEANUP.md"
echo "To rollback: rm -rf utils docs archive && cp -r $BACKUP_DIR/* ."
echo "======================================================================="
