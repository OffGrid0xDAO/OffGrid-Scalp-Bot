"""
Fix Dependencies - Copy back all required files from scratches
"""

import shutil
from pathlib import Path

# Files that dual_timeframe_bot.py needs
required_files = [
    'claude_trader.py',
    'telegram_notifier.py',
    'continuous_learning.py',
]

print("🔧 Fixing dependencies...\n")

scratches = Path('scratches')
copied = 0

for file in required_files:
    src = scratches / file
    dest = Path(file)

    if src.exists():
        if not dest.exists():
            shutil.copy(src, dest)
            print(f"✅ Copied: {file}")
            copied += 1
        else:
            print(f"⏭️  Already exists: {file}")
    else:
        print(f"⚠️  Not found in scratches: {file}")

print(f"\n✅ Fixed! Copied {copied} files back.")
print("\nTry running again: python3 run_dual_bot_optimized.py")
