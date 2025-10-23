#!/bin/bash

# Create new clean structure
mkdir -p src/data
mkdir -p src/indicators
mkdir -p src/analysis
mkdir -p src/strategy
mkdir -p src/backtest
mkdir -p src/optimization
mkdir -p src/live
mkdir -p src/utils

mkdir -p tests
mkdir -p configs
mkdir -p logs

echo "✅ Created new project structure:"
tree -L 2 -d src/ 2>/dev/null || find src/ -type d
