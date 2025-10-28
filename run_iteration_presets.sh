#!/bin/bash
# Quick presets for running automated iterations

echo "🤖 AUTOMATED ITERATION PRESETS"
echo "=============================="
echo ""
echo "Choose a preset:"
echo ""
echo "1) Conservative   - Sharpe 12.0, Return 4.0%  (Ultra-safe)"
echo "2) Balanced       - Sharpe 9.0,  Return 6.0%  (Recommended)"
echo "3) Aggressive     - Sharpe 7.0,  Return 8.0%  (Higher returns)"
echo "4) Very Aggressive- Sharpe 5.0,  Return 10.0% (Max returns)"
echo "5) Custom         - Enter your own targets"
echo ""
read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🛡️  Running CONSERVATIVE preset..."
        echo "Target: Sharpe 12.0, Return 4.0%"
        echo ""
        python iterate_backtest.py --iterations 15 --target-sharpe 12.0 --target-return 4.0
        ;;
    2)
        echo ""
        echo "⚖️  Running BALANCED preset (RECOMMENDED)..."
        echo "Target: Sharpe 9.0, Return 6.0%"
        echo ""
        python iterate_backtest.py --iterations 15 --target-sharpe 9.0 --target-return 6.0
        ;;
    3)
        echo ""
        echo "🚀 Running AGGRESSIVE preset..."
        echo "Target: Sharpe 7.0, Return 8.0%"
        echo ""
        python iterate_backtest.py --iterations 20 --target-sharpe 7.0 --target-return 8.0
        ;;
    4)
        echo ""
        echo "⚡ Running VERY AGGRESSIVE preset..."
        echo "Target: Sharpe 5.0, Return 10.0%"
        echo ""
        python iterate_backtest.py --iterations 20 --target-sharpe 5.0 --target-return 10.0
        ;;
    5)
        echo ""
        read -p "Target Sharpe ratio: " sharpe
        read -p "Target Return %: " returns
        read -p "Max iterations: " iters
        echo ""
        echo "🎯 Running CUSTOM preset..."
        echo "Target: Sharpe $sharpe, Return $returns%"
        echo ""
        python iterate_backtest.py --iterations $iters --target-sharpe $sharpe --target-return $returns
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Iteration complete!"
echo ""
echo "📁 Results saved to: iteration_results/"
echo ""
echo "📊 View summary:"
echo "   cat iteration_results/iteration_summary.json | python -m json.tool"
echo ""
echo "📈 View best parameters:"
echo "   cat iteration_results/iteration_summary.json | grep -A 10 'final_params'"
echo ""
