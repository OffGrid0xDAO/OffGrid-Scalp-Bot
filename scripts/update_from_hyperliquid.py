#!/usr/bin/env python3
"""
Hyperliquid Data Updater

Fetches latest candle data from Hyperliquid API to keep local data fresh.
Designed for continuous operation by live trading bot.

Features:
- Fetches missing candles since last data point
- Appends to existing CSV files
- Triggers indicator recalculation
- Optionally regenerates charts
- Can run once or in continuous loop
"""

import sys
import os
from pathlib import Path
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class HyperliquidDataUpdater:
    """
    Fetch and update data from Hyperliquid API

    Hyperliquid API Info:
    - Endpoint: POST https://api.hyperliquid.xyz/info
    - Max candles per request: 5000
    - Timeframes: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 3d, 1w, 1M
    """

    def __init__(
        self,
        symbol: str = 'ETH',
        timeframes: list = None,
        data_dir: str = 'trading_data/raw',
        api_url: str = 'https://api.hyperliquid.xyz/info'
    ):
        """
        Initialize Hyperliquid data updater

        Args:
            symbol: Trading symbol (default: ETH)
            timeframes: List of timeframes to update (default: all)
            data_dir: Directory containing raw CSV files
            api_url: Hyperliquid API endpoint
        """
        self.symbol = symbol.upper()
        self.timeframes = timeframes or ['1m', '3m', '5m', '15m', '30m', '1h']
        self.data_dir = Path(data_dir)
        self.api_url = api_url

        print(f"🔧 Hyperliquid Data Updater")
        print(f"   Symbol: {self.symbol}")
        print(f"   Timeframes: {', '.join(self.timeframes)}")
        print(f"   Data dir: {self.data_dir}")

    def fetch_candles(
        self,
        timeframe: str,
        start_time_ms: int,
        end_time_ms: int = None
    ) -> list:
        """
        Fetch candles from Hyperliquid API

        Args:
            timeframe: Candle timeframe (1m, 5m, 1h, etc.)
            start_time_ms: Start time in milliseconds
            end_time_ms: End time in milliseconds (default: now)

        Returns:
            List of candle dictionaries
        """
        if end_time_ms is None:
            end_time_ms = int(datetime.now().timestamp() * 1000)

        print(f"\n📡 Fetching {timeframe} candles from Hyperliquid...")
        print(f"   Range: {datetime.fromtimestamp(start_time_ms/1000)} to {datetime.fromtimestamp(end_time_ms/1000)}")

        payload = {
            'type': 'candleSnapshot',
            'req': {
                'coin': self.symbol,
                'interval': timeframe,
                'startTime': start_time_ms,
                'endTime': end_time_ms
            }
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()

            candles = response.json()

            if not candles:
                print(f"   ⚠️  No new candles available")
                return []

            print(f"   ✅ Fetched {len(candles)} candles")
            return candles

        except requests.exceptions.RequestException as e:
            print(f"   ❌ API request failed: {e}")
            return []
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []

    def convert_candles_to_df(self, candles: list) -> pd.DataFrame:
        """
        Convert Hyperliquid candles to DataFrame

        Hyperliquid candle format:
        - T: Timestamp (milliseconds)
        - o: Open price
        - h: High price
        - l: Low price
        - c: Close price
        - v: Volume

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame([{
            'timestamp': datetime.fromtimestamp(c['T'] / 1000).strftime('%Y-%m-%dT%H:%M:%S'),
            'open': float(c['o']),
            'high': float(c['h']),
            'low': float(c['l']),
            'close': float(c['c']),
            'volume': float(c['v'])
        } for c in candles])

        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)

        return df

    def get_last_timestamp(self, timeframe: str) -> datetime:
        """
        Get last timestamp from existing CSV file

        Args:
            timeframe: Timeframe string (1m, 5m, etc.)

        Returns:
            Last timestamp as datetime, or None if file doesn't exist
        """
        csv_path = self.data_dir / f'{self.symbol.lower()}_historical_{timeframe}.csv'

        if not csv_path.exists():
            print(f"   ⚠️  File not found: {csv_path}")
            return None

        try:
            # Read only the timestamp column from last row
            df = pd.read_csv(csv_path, usecols=['timestamp'])

            if df.empty:
                return None

            last_ts = df['timestamp'].iloc[-1]
            last_dt = pd.to_datetime(last_ts)

            print(f"   📅 Last timestamp in file: {last_dt}")
            return last_dt

        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            return None

    def append_to_csv(self, new_data: pd.DataFrame, timeframe: str) -> bool:
        """
        Append new data to existing CSV file

        Args:
            new_data: DataFrame with new candles (only OHLCV columns)
            timeframe: Timeframe string

        Returns:
            True if successful
        """
        if new_data.empty:
            print(f"   ⚠️  No new data to append")
            return False

        csv_path = self.data_dir / f'{self.symbol.lower()}_historical_{timeframe}.csv'

        try:
            # Ensure only OHLCV columns (indicators will be recalculated)
            new_data = new_data[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

            if csv_path.exists():
                # Read existing data (only OHLCV columns)
                existing_df = pd.read_csv(csv_path, usecols=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                # Combine and remove duplicates
                combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
                combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)

                # Save back
                combined_df.to_csv(csv_path, index=False)

                new_count = len(combined_df) - len(existing_df)
                print(f"   ✅ Appended {new_count} new candles to {csv_path}")
                print(f"   📊 Total candles: {len(combined_df)}")

            else:
                # Create new file
                new_data.to_csv(csv_path, index=False)
                print(f"   ✅ Created new file: {csv_path}")
                print(f"   📊 Total candles: {len(new_data)}")

            return True

        except Exception as e:
            print(f"   ❌ Error appending to CSV: {e}")
            return False

    def update_timeframe(self, timeframe: str) -> bool:
        """
        Update data for a single timeframe

        Args:
            timeframe: Timeframe string (1m, 5m, etc.)

        Returns:
            True if new data was fetched and appended
        """
        print(f"\n{'='*80}")
        print(f"📊 Updating {timeframe} data")
        print(f"{'='*80}")

        # Get last timestamp from file
        last_dt = self.get_last_timestamp(timeframe)

        if last_dt is None:
            # No existing data - fetch last 5000 candles
            print(f"   ℹ️  No existing data - fetching last 5000 candles")
            end_time_ms = int(datetime.now().timestamp() * 1000)

            # Calculate start time based on timeframe
            # Approximate: fetch enough to get 5000 candles
            timeframe_minutes = self._parse_timeframe_minutes(timeframe)
            start_time_ms = end_time_ms - (5000 * timeframe_minutes * 60 * 1000)

        else:
            # Fetch from last timestamp to now
            start_time_ms = int(last_dt.timestamp() * 1000)
            end_time_ms = int(datetime.now().timestamp() * 1000)

            # Check if we need to fetch
            time_diff = (datetime.now() - last_dt).total_seconds() / 60
            timeframe_minutes = self._parse_timeframe_minutes(timeframe)

            if time_diff < timeframe_minutes:
                print(f"   ✅ Data is up-to-date (last candle was {time_diff:.1f} minutes ago)")
                return False

        # Fetch candles
        candles = self.fetch_candles(timeframe, start_time_ms, end_time_ms)

        if not candles:
            return False

        # Convert to DataFrame
        df = self.convert_candles_to_df(candles)

        # Append to CSV
        success = self.append_to_csv(df, timeframe)

        return success

    def _parse_timeframe_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 1440
        else:
            return 60  # Default to 1h

    def update_all_timeframes(self) -> bool:
        """
        Update data for all configured timeframes

        Returns:
            True if any timeframe was updated
        """
        print(f"\n{'='*80}")
        print(f"🚀 UPDATING ALL TIMEFRAMES")
        print(f"{'='*80}")

        updated = []

        for tf in self.timeframes:
            if self.update_timeframe(tf):
                updated.append(tf)

        print(f"\n{'='*80}")
        if updated:
            print(f"✅ Updated timeframes: {', '.join(updated)}")
            return True
        else:
            print(f"✅ All timeframes are up-to-date")
            return False

    def recalculate_indicators(self) -> bool:
        """
        Trigger indicator recalculation by running process_indicators.py

        Returns:
            True if successful
        """
        print(f"\n{'='*80}")
        print(f"📊 RECALCULATING INDICATORS")
        print(f"{'='*80}")

        script_path = Path(__file__).parent / 'process_indicators.py'

        if not script_path.exists():
            print(f"   ❌ Script not found: {script_path}")
            return False

        try:
            result = subprocess.run(
                ['python3', str(script_path)],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                print(f"   ✅ Indicators recalculated successfully")
                # Print last 20 lines of output
                output_lines = result.stdout.split('\n')
                for line in output_lines[-20:]:
                    if line.strip():
                        print(f"   {line}")
                return True
            else:
                print(f"   ❌ Indicator calculation failed")
                print(f"   Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"   ❌ Indicator calculation timed out")
            return False
        except Exception as e:
            print(f"   ❌ Error running indicator calculation: {e}")
            return False

    def regenerate_charts(self) -> bool:
        """
        Trigger chart regeneration by running create_charts.py

        Returns:
            True if successful
        """
        print(f"\n{'='*80}")
        print(f"📈 REGENERATING CHARTS")
        print(f"{'='*80}")

        script_path = Path(__file__).parent / 'create_charts.py'

        if not script_path.exists():
            print(f"   ❌ Script not found: {script_path}")
            return False

        try:
            result = subprocess.run(
                ['python3', str(script_path)],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                print(f"   ✅ Charts regenerated successfully")
                # Print last 20 lines of output
                output_lines = result.stdout.split('\n')
                for line in output_lines[-20:]:
                    if line.strip():
                        print(f"   {line}")
                return True
            else:
                print(f"   ❌ Chart generation failed")
                print(f"   Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"   ❌ Chart generation timed out")
            return False
        except Exception as e:
            print(f"   ❌ Error running chart generation: {e}")
            return False

    def run_once(self, recalc_indicators: bool = True, regen_charts: bool = False) -> bool:
        """
        Run a single update cycle

        Args:
            recalc_indicators: Whether to recalculate indicators
            regen_charts: Whether to regenerate charts

        Returns:
            True if any updates were made
        """
        # Update all timeframes
        updated = self.update_all_timeframes()

        if not updated:
            print(f"\n✅ No updates needed")
            return False

        # Recalculate indicators if requested
        if recalc_indicators:
            self.recalculate_indicators()

        # Regenerate charts if requested
        if regen_charts:
            self.regenerate_charts()

        return True

    def run_continuous(
        self,
        interval_minutes: int = 5,
        recalc_indicators: bool = True,
        regen_charts: bool = False
    ):
        """
        Run continuous updates in a loop

        Args:
            interval_minutes: Minutes between update checks
            recalc_indicators: Whether to recalculate indicators after updates
            regen_charts: Whether to regenerate charts after updates
        """
        print(f"\n{'='*80}")
        print(f"🔄 CONTINUOUS UPDATE MODE")
        print(f"{'='*80}")
        print(f"   Update interval: {interval_minutes} minutes")
        print(f"   Recalculate indicators: {recalc_indicators}")
        print(f"   Regenerate charts: {regen_charts}")
        print(f"   Press Ctrl+C to stop")
        print(f"{'='*80}")

        try:
            while True:
                print(f"\n\n⏰ Update cycle started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                self.run_once(recalc_indicators, regen_charts)

                print(f"\n💤 Sleeping for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Continuous update stopped by user")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Update trading data from Hyperliquid API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once (fetch new data + recalculate indicators)
  python3 scripts/update_from_hyperliquid.py

  # Run once with chart regeneration
  python3 scripts/update_from_hyperliquid.py --charts

  # Run continuously (check every 5 minutes)
  python3 scripts/update_from_hyperliquid.py --continuous

  # Run continuously with custom interval (check every 15 minutes)
  python3 scripts/update_from_hyperliquid.py --continuous --interval 15

  # Run continuously with full pipeline (data + indicators + charts)
  python3 scripts/update_from_hyperliquid.py --continuous --charts --interval 30
        """
    )

    parser.add_argument(
        '--symbol',
        default='ETH',
        help='Trading symbol (default: ETH)'
    )

    parser.add_argument(
        '--timeframes',
        nargs='+',
        default=['1m', '3m', '5m', '15m', '30m', '1h'],
        help='Timeframes to update (default: all)'
    )

    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously instead of once'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Minutes between updates in continuous mode (default: 5)'
    )

    parser.add_argument(
        '--no-indicators',
        action='store_true',
        help='Skip indicator recalculation'
    )

    parser.add_argument(
        '--charts',
        action='store_true',
        help='Regenerate charts after updates'
    )

    args = parser.parse_args()

    # Create updater
    updater = HyperliquidDataUpdater(
        symbol=args.symbol,
        timeframes=args.timeframes
    )

    # Run
    if args.continuous:
        updater.run_continuous(
            interval_minutes=args.interval,
            recalc_indicators=not args.no_indicators,
            regen_charts=args.charts
        )
    else:
        updater.run_once(
            recalc_indicators=not args.no_indicators,
            regen_charts=args.charts
        )


if __name__ == '__main__':
    main()
