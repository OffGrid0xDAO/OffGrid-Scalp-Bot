"""
Parameter Optimization for Fourier Trading Strategy

This script performs sensitivity analysis and parameter optimization
for the Fourier Trading Strategy.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from itertools import product
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import warnings

from fourier_strategy import FourierTradingStrategy

warnings.filterwarnings('ignore')


class ParameterOptimizer:
    """
    Parameter optimizer for Fourier Trading Strategy.

    Performs grid search and sensitivity analysis.
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize optimizer.

        Args:
            df: OHLCV DataFrame for testing
        """
        self.df = df
        self.results = []

    def grid_search(self,
                   param_grid: Dict[str, List],
                   metric: str = 'sharpe_ratio',
                   verbose: bool = True) -> pd.DataFrame:
        """
        Perform grid search over parameter space.

        Args:
            param_grid: Dictionary of parameters to test
            metric: Metric to optimize ('sharpe_ratio', 'total_return_pct', etc.)
            verbose: Print progress

        Returns:
            DataFrame with all results
        """
        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))

        total_combinations = len(combinations)

        if verbose:
            print(f"Testing {total_combinations} parameter combinations...")
            print("=" * 70)

        results = []

        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))

            if verbose and (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{total_combinations} ({(i+1)/total_combinations*100:.1f}%)")

            try:
                # Create strategy with these parameters
                strategy = FourierTradingStrategy(**params)

                # Run backtest
                output = strategy.run(self.df, run_backtest=True, verbose=False)

                metrics = output['metrics']

                # Store results
                result = params.copy()
                result['sharpe_ratio'] = metrics['sharpe_ratio']
                result['total_return_pct'] = metrics['total_return_pct']
                result['max_drawdown_pct'] = metrics['max_drawdown_pct']
                result['win_rate_pct'] = metrics['win_rate_pct']
                result['profit_factor'] = metrics['profit_factor']
                result['num_trades'] = metrics['num_trades']

                results.append(result)

            except Exception as e:
                if verbose:
                    print(f"Error with params {params}: {e}")
                continue

        results_df = pd.DataFrame(results)

        # Sort by metric
        results_df = results_df.sort_values(metric, ascending=False)

        self.results = results_df

        if verbose:
            print("\n" + "=" * 70)
            print(f"Grid search complete. Best {metric}: {results_df[metric].iloc[0]:.2f}")
            print("=" * 70)

        return results_df

    def sensitivity_analysis(self,
                            param_name: str,
                            param_values: List,
                            base_params: Dict = None,
                            metric: str = 'sharpe_ratio') -> pd.DataFrame:
        """
        Analyze sensitivity to a single parameter.

        Args:
            param_name: Parameter to vary
            param_values: Values to test
            base_params: Base parameter set
            metric: Metric to track

        Returns:
            DataFrame with sensitivity results
        """
        if base_params is None:
            base_params = {}

        print(f"Sensitivity analysis for: {param_name}")
        print(f"Testing {len(param_values)} values: {param_values}")
        print("=" * 70)

        results = []

        for value in param_values:
            params = base_params.copy()
            params[param_name] = value

            try:
                strategy = FourierTradingStrategy(**params)
                output = strategy.run(self.df, run_backtest=True, verbose=False)
                metrics = output['metrics']

                results.append({
                    param_name: value,
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'total_return_pct': metrics['total_return_pct'],
                    'max_drawdown_pct': metrics['max_drawdown_pct'],
                    'win_rate_pct': metrics['win_rate_pct'],
                    'num_trades': metrics['num_trades']
                })

            except Exception as e:
                print(f"Error with {param_name}={value}: {e}")
                continue

        results_df = pd.DataFrame(results)

        print(f"\nBest {metric}: {results_df[metric].max():.2f} at {param_name}={results_df.loc[results_df[metric].idxmax(), param_name]}")

        return results_df

    def plot_sensitivity(self,
                        sensitivity_results: pd.DataFrame,
                        param_name: str,
                        save_path: str = None):
        """
        Plot sensitivity analysis results.

        Args:
            sensitivity_results: Results from sensitivity_analysis
            param_name: Parameter name
            save_path: Optional save path
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Sharpe Ratio
        ax1 = axes[0, 0]
        ax1.plot(sensitivity_results[param_name], sensitivity_results['sharpe_ratio'],
                marker='o', linewidth=2)
        ax1.set_title(f'Sharpe Ratio vs {param_name}', fontweight='bold')
        ax1.set_xlabel(param_name)
        ax1.set_ylabel('Sharpe Ratio')
        ax1.grid(True, alpha=0.3)

        # Total Return
        ax2 = axes[0, 1]
        ax2.plot(sensitivity_results[param_name], sensitivity_results['total_return_pct'],
                marker='o', linewidth=2, color='green')
        ax2.set_title(f'Total Return vs {param_name}', fontweight='bold')
        ax2.set_xlabel(param_name)
        ax2.set_ylabel('Total Return (%)')
        ax2.grid(True, alpha=0.3)

        # Max Drawdown
        ax3 = axes[1, 0]
        ax3.plot(sensitivity_results[param_name], sensitivity_results['max_drawdown_pct'],
                marker='o', linewidth=2, color='red')
        ax3.set_title(f'Max Drawdown vs {param_name}', fontweight='bold')
        ax3.set_xlabel(param_name)
        ax3.set_ylabel('Max Drawdown (%)')
        ax3.grid(True, alpha=0.3)

        # Win Rate
        ax4 = axes[1, 1]
        ax4.plot(sensitivity_results[param_name], sensitivity_results['win_rate_pct'],
                marker='o', linewidth=2, color='orange')
        ax4.set_title(f'Win Rate vs {param_name}', fontweight='bold')
        ax4.set_xlabel(param_name)
        ax4.set_ylabel('Win Rate (%)')
        ax4.grid(True, alpha=0.3)

        plt.suptitle(f'Sensitivity Analysis: {param_name}', fontsize=16, fontweight='bold')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig

    def plot_parameter_heatmap(self,
                              grid_results: pd.DataFrame,
                              param1: str,
                              param2: str,
                              metric: str = 'sharpe_ratio',
                              save_path: str = None):
        """
        Plot 2D heatmap of parameter combinations.

        Args:
            grid_results: Results from grid_search
            param1: First parameter name
            param2: Second parameter name
            metric: Metric to visualize
            save_path: Optional save path
        """
        # Pivot data
        pivot_data = grid_results.pivot_table(
            values=metric,
            index=param1,
            columns=param2,
            aggfunc='mean'
        )

        fig, ax = plt.subplots(figsize=(10, 8))

        sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='RdYlGn',
                   center=0, ax=ax, cbar_kws={'label': metric})

        ax.set_title(f'{metric} Heatmap: {param1} vs {param2}', fontweight='bold')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig


def example_grid_search():
    """Example: Grid search over key parameters."""
    print("=" * 70)
    print("PARAMETER OPTIMIZATION - GRID SEARCH")
    print("=" * 70)

    # Fetch data
    print("\nFetching data...")
    df = yf.download('BTC-USD', period='1y', interval='1d', progress=False)
    df.columns = [col.lower() for col in df.columns]

    # Initialize optimizer
    optimizer = ParameterOptimizer(df)

    # Define parameter grid (smaller for speed)
    param_grid = {
        'n_harmonics': [3, 5, 7],
        'noise_threshold': [0.2, 0.3, 0.4],
        'correlation_threshold': [0.6, 0.7, 0.8],
        'min_signal_strength': [0.4, 0.5, 0.6]
    }

    # Run grid search
    results = optimizer.grid_search(param_grid, metric='sharpe_ratio', verbose=True)

    # Show top 10 results
    print("\nTop 10 Parameter Combinations:")
    print("=" * 70)
    print(results.head(10).to_string(index=False))

    # Best parameters
    best_params = results.iloc[0].to_dict()
    print(f"\nBest Parameters:")
    for key, value in best_params.items():
        if key not in ['sharpe_ratio', 'total_return_pct', 'max_drawdown_pct',
                      'win_rate_pct', 'profit_factor', 'num_trades']:
            print(f"  {key}: {value}")

    # Save results
    results.to_csv('fourier_grid_search_results.csv', index=False)
    print("\nResults saved to: fourier_grid_search_results.csv")

    return optimizer, results


def example_sensitivity_analysis():
    """Example: Sensitivity analysis for individual parameters."""
    print("\n" + "=" * 70)
    print("SENSITIVITY ANALYSIS")
    print("=" * 70)

    # Fetch data
    df = yf.download('BTC-USD', period='1y', interval='1d', progress=False)
    df.columns = [col.lower() for col in df.columns]

    optimizer = ParameterOptimizer(df)

    # Test n_harmonics
    print("\n1. Testing n_harmonics...")
    harmonics_results = optimizer.sensitivity_analysis(
        param_name='n_harmonics',
        param_values=[3, 5, 7, 9, 11],
        metric='sharpe_ratio'
    )

    optimizer.plot_sensitivity(harmonics_results, 'n_harmonics',
                              save_path='sensitivity_n_harmonics.png')

    # Test noise_threshold
    print("\n2. Testing noise_threshold...")
    noise_results = optimizer.sensitivity_analysis(
        param_name='noise_threshold',
        param_values=[0.1, 0.2, 0.3, 0.4, 0.5],
        metric='sharpe_ratio'
    )

    optimizer.plot_sensitivity(noise_results, 'noise_threshold',
                              save_path='sensitivity_noise_threshold.png')

    # Test base_ema_period
    print("\n3. Testing base_ema_period...")
    ema_results = optimizer.sensitivity_analysis(
        param_name='base_ema_period',
        param_values=[14, 21, 28, 35, 50],
        metric='sharpe_ratio'
    )

    optimizer.plot_sensitivity(ema_results, 'base_ema_period',
                              save_path='sensitivity_ema_period.png')

    # Test correlation_threshold
    print("\n4. Testing correlation_threshold...")
    corr_results = optimizer.sensitivity_analysis(
        param_name='correlation_threshold',
        param_values=[0.5, 0.6, 0.7, 0.8, 0.9],
        metric='sharpe_ratio'
    )

    optimizer.plot_sensitivity(corr_results, 'correlation_threshold',
                              save_path='sensitivity_correlation.png')

    plt.show()

    return optimizer, {
        'harmonics': harmonics_results,
        'noise': noise_results,
        'ema': ema_results,
        'correlation': corr_results
    }


def example_2d_heatmap():
    """Example: 2D heatmap of parameter interactions."""
    print("\n" + "=" * 70)
    print("2D PARAMETER HEATMAP")
    print("=" * 70)

    # Fetch data
    df = yf.download('BTC-USD', period='6mo', interval='1d', progress=False)
    df.columns = [col.lower() for col in df.columns]

    optimizer = ParameterOptimizer(df)

    # Grid for 2D analysis
    param_grid = {
        'n_harmonics': [3, 5, 7, 9],
        'noise_threshold': [0.2, 0.3, 0.4, 0.5]
    }

    results = optimizer.grid_search(param_grid, verbose=True)

    # Plot heatmap
    optimizer.plot_parameter_heatmap(
        results,
        'n_harmonics',
        'noise_threshold',
        metric='sharpe_ratio',
        save_path='heatmap_harmonics_vs_noise.png'
    )

    plt.show()

    return optimizer, results


if __name__ == '__main__':
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 12 + "FOURIER STRATEGY OPTIMIZATION" + " " * 25 + "║")
    print("╚" + "═" * 68 + "╝\n")

    # Choose which optimizations to run
    run_optimizations = {
        'grid_search': True,
        'sensitivity': False,
        'heatmap': False
    }

    if run_optimizations['grid_search']:
        opt1, results1 = example_grid_search()

    if run_optimizations['sensitivity']:
        opt2, results2 = example_sensitivity_analysis()

    if run_optimizations['heatmap']:
        opt3, results3 = example_2d_heatmap()

    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
