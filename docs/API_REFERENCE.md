# API Reference

Complete API documentation for the TradingScalper trading bot system.

---

## Table of Contents

- [Exchange Module](#exchange-module)
- [Strategy Module](#strategy-module)
- [Indicators Module](#indicators-module)
- [Data Module](#data-module)
- [Backtest Module](#backtest-module)
- [Notifications Module](#notifications-module)
- [Reporting Module](#reporting-module)
- [Analysis Module](#analysis-module)
- [Optimization Module](#optimization-module)

---

## Exchange Module

### HyperliquidClient

**Location:** `src/exchange/hyperliquid_client.py`

Handles all interactions with the Hyperliquid DEX API.

#### Constructor

```python
HyperliquidClient(testnet: bool = False)
```

**Parameters:**
- `testnet` (bool): If True, connects to testnet. If False, connects to mainnet. Default: False.

**Attributes:**
- `enabled` (bool): Whether the client is properly initialized
- `testnet` (bool): Current network mode
- `private_key` (str): Wallet private key from environment

#### Methods

##### `get_account_info()`

Fetches current account information including balance and positions.

**Returns:**
- `dict`: Account information including:
  - `marginSummary`: Account value, available balance, etc.
  - `assetPositions`: Open positions

**Raises:**
- `Exception`: If API call fails

**Example:**
```python
client = HyperliquidClient(testnet=False)
info = client.get_account_info()
balance = float(info['marginSummary']['accountValue'])
print(f"Account Balance: ${balance:.2f}")
```

##### `get_current_price(symbol: str)`

Gets the current market price for a symbol.

**Parameters:**
- `symbol` (str): Trading symbol (e.g., 'ETH', 'BTC')

**Returns:**
- `float`: Current market price

**Example:**
```python
price = client.get_current_price('ETH')
print(f"ETH Price: ${price:.2f}")
```

##### `place_market_order(symbol: str, side: str, size: float, reduce_only: bool = False)`

Places a market order on the exchange.

**Parameters:**
- `symbol` (str): Trading symbol
- `side` (str): Order side ('buy' or 'sell')
- `size` (float): Order size in base asset units
- `reduce_only` (bool): If True, order can only reduce existing position

**Returns:**
- `dict`: Order result containing:
  - `status`: 'ok' or error status
  - `filled_price`: Execution price
  - `filled_size`: Executed size

**Example:**
```python
order = client.place_market_order(
    symbol='ETH',
    side='buy',
    size=0.1,
    reduce_only=False
)
```

##### `enter_trade(symbol: str, direction: str, size_usd: float, tp_pct: float, sl_pct: float)`

Enters a new trade with automatic TP/SL placement.

**Parameters:**
- `symbol` (str): Trading symbol
- `direction` (str): 'long' or 'short'
- `size_usd` (float): Position size in USD
- `tp_pct` (float): Take profit percentage
- `sl_pct` (float): Stop loss percentage

**Returns:**
- `dict`: Trade result containing:
  - `success` (bool): Whether trade was entered successfully
  - `entry_price` (float): Actual entry price
  - `size` (float): Position size

**Example:**
```python
result = client.enter_trade(
    symbol='ETH',
    direction='long',
    size_usd=100,
    tp_pct=5.0,
    sl_pct=0.75
)
```

---

## Strategy Module

### EntryDetector

**Location:** `src/strategy/entry_detector_user_pattern.py`

Detects entry signals based on Iteration 10 strategy parameters.

#### Constructor

```python
EntryDetector(df_5m: pd.DataFrame, df_15m: pd.DataFrame, params: dict = None)
```

**Parameters:**
- `df_5m` (DataFrame): 5-minute timeframe data with indicators
- `df_15m` (DataFrame): 15-minute timeframe data with indicators
- `params` (dict, optional): Strategy parameters. Loads from `strategy_params.json` if not provided.

#### Methods

##### `scan_historical_signals(df: pd.DataFrame)`

Scans historical data for entry signals.

**Parameters:**
- `df` (DataFrame): Price data with indicators

**Returns:**
- `DataFrame`: Input dataframe with additional columns:
  - `entry_signal` (bool): Whether entry signal detected
  - `entry_direction` (str): 'long', 'short', or None
  - `entry_quality_score` (float): Signal quality score (0-100)
  - `entry_reason` (str): Description of entry logic

**Example:**
```python
detector = EntryDetector(df_5m, df_15m)
df_signals = detector.scan_historical_signals(df_15m)

# Get last signal
last_signal = df_signals.iloc[-1]
if last_signal['entry_signal']:
    print(f"Signal: {last_signal['entry_direction']}")
    print(f"Quality: {last_signal['entry_quality_score']:.0f}/100")
```

##### `calculate_quality_score(row: pd.Series)`

Calculates signal quality based on indicator confluence.

**Parameters:**
- `row` (Series): DataFrame row with indicator values

**Returns:**
- `float`: Quality score from 0-100

**Quality Components:**
- RSI alignment: 0-30 points
- Stochastic alignment: 0-25 points
- Volume confirmation: 0-20 points
- Confluence gap: 0-25 points

### ExitManager

**Location:** `src/strategy/exit_manager_user_pattern.py`

Manages trade exits based on TP/SL and profit lock logic.

#### Constructor

```python
ExitManager(params: dict = None)
```

**Parameters:**
- `params` (dict, optional): Exit strategy parameters

#### Methods

##### `check_exit(entry_price: float, entry_time: datetime, current_price: float, current_time: datetime, direction: str, peak_profit_pct: float)`

Checks if position should be exited.

**Parameters:**
- `entry_price` (float): Entry price
- `entry_time` (datetime): Entry timestamp
- `current_price` (float): Current market price
- `current_time` (datetime): Current timestamp
- `direction` (str): 'long' or 'short'
- `peak_profit_pct` (float): Maximum profit reached

**Returns:**
- `dict`: Exit decision containing:
  - `should_exit` (bool): Whether to exit
  - `exit_reason` (str): Reason for exit
  - `profit_pct` (float): Current profit percentage

**Exit Conditions:**
1. Take profit hit (default: +5.0%)
2. Stop loss hit (default: -0.75%)
3. Profit lock engaged (after +1.5%, won't let trade go negative)

**Example:**
```python
exit_mgr = ExitManager()
result = exit_mgr.check_exit(
    entry_price=2500.0,
    entry_time=datetime.now(),
    current_price=2520.0,
    current_time=datetime.now(),
    direction='long',
    peak_profit_pct=1.0
)

if result['should_exit']:
    print(f"Exit: {result['exit_reason']}")
    print(f"Profit: {result['profit_pct']:+.2f}%")
```

---

## Indicators Module

### IndicatorPipeline

**Location:** `src/indicators/indicator_pipeline.py`

Calculates all technical indicators for a dataset.

#### Constructor

```python
IndicatorPipeline()
```

#### Methods

##### `calculate_all(df: pd.DataFrame, timeframe: str = '15m')`

Calculates all indicators for the given dataframe.

**Parameters:**
- `df` (DataFrame): OHLCV price data
- `timeframe` (str): Timeframe label for context

**Returns:**
- `DataFrame`: Input data with calculated indicators:
  - EMAs: 8, 13, 21, 34, 55, 89, 144, 233 periods
  - RSI: 7 and 14 periods
  - Stochastic: %K and %D
  - MACD: Standard and fast settings
  - Bollinger Bands: 20-period
  - Volume: Ratio and profile
  - VWAP: Volume-weighted average price

**Example:**
```python
pipeline = IndicatorPipeline()
df = pd.read_csv('eth_15m.csv')
df_indicators = pipeline.calculate_all(df, timeframe='15m')
```

### RSICalculator

**Location:** `src/indicators/rsi_calculator.py`

Calculates Relative Strength Index.

#### Methods

##### `calculate(df: pd.DataFrame, period: int = 14)`

**Parameters:**
- `df` (DataFrame): Price data with 'close' column
- `period` (int): RSI period (default: 14)

**Returns:**
- `DataFrame`: Input data with `rsi_{period}` column added

**Interpretation:**
- RSI > 70: Overbought
- RSI < 30: Oversold
- RSI 40-60: Neutral

### MACDCalculator

**Location:** `src/indicators/macd_calculator.py`

Calculates Moving Average Convergence Divergence.

#### Methods

##### `calculate(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9)`

**Parameters:**
- `df` (DataFrame): Price data with 'close' column
- `fast` (int): Fast EMA period
- `slow` (int): Slow EMA period
- `signal` (int): Signal line period

**Returns:**
- `DataFrame`: Input data with columns added:
  - `macd`: MACD line
  - `macd_signal`: Signal line
  - `macd_histogram`: MACD histogram

**Signals:**
- Bullish: MACD crosses above signal
- Bearish: MACD crosses below signal

### VWAPCalculator

**Location:** `src/indicators/vwap_calculator.py`

Calculates Volume-Weighted Average Price.

#### Methods

##### `calculate(df: pd.DataFrame)`

**Parameters:**
- `df` (DataFrame): Price data with OHLCV columns

**Returns:**
- `DataFrame`: Input data with `vwap` column added

**Usage:**
- Price above VWAP: Bullish
- Price below VWAP: Bearish

---

## Data Module

### HyperliquidFetcher

**Location:** `src/data/hyperliquid_fetcher.py`

Fetches historical OHLCV data from Hyperliquid API.

#### Constructor

```python
HyperliquidFetcher(symbol: str = 'ETH')
```

**Parameters:**
- `symbol` (str): Trading symbol to fetch

#### Methods

##### `fetch_ohlcv(timeframe: str, start_date: datetime, end_date: datetime, output_file: str = None)`

Fetches OHLCV data for specified timeframe and date range.

**Parameters:**
- `timeframe` (str): Candle timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
- `start_date` (datetime): Start of date range
- `end_date` (datetime): End of date range
- `output_file` (str, optional): Path to save CSV output

**Returns:**
- `DataFrame`: OHLCV data with columns:
  - `timestamp`: Candle timestamp
  - `open`, `high`, `low`, `close`: Price data
  - `volume`: Trading volume

**Example:**
```python
fetcher = HyperliquidFetcher(symbol='ETH')
df = fetcher.fetch_ohlcv(
    timeframe='15m',
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 10, 24),
    output_file='eth_15m.csv'
)
```

---

## Backtest Module

### BacktestEngine

**Location:** `src/backtest/backtest_engine.py`

Runs backtests of trading strategies on historical data.

#### Constructor

```python
BacktestEngine(initial_capital: float = 1000, position_size_pct: float = 10.0, leverage: float = 1.0)
```

**Parameters:**
- `initial_capital` (float): Starting capital
- `position_size_pct` (float): Position size as % of capital
- `leverage` (float): Trading leverage

#### Methods

##### `run_backtest(df: pd.DataFrame, strategy_name: str = 'default')`

Runs backtest on provided data.

**Parameters:**
- `df` (DataFrame): Historical data with indicators and signals
- `strategy_name` (str): Name for this backtest

**Returns:**
- `dict`: Backtest results containing:
  - `trades`: List of all trades executed
  - `total_return_pct`: Overall return percentage
  - `win_rate`: Winning trades percentage
  - `profit_factor`: Gross profit / gross loss
  - `max_drawdown`: Maximum equity drawdown
  - `sharpe_ratio`: Risk-adjusted return

**Example:**
```python
engine = BacktestEngine(initial_capital=1000)
results = engine.run_backtest(df_with_signals, strategy_name='Iteration_10')

print(f"Return: {results['total_return_pct']:+.2f}%")
print(f"Win Rate: {results['win_rate']:.1f}%")
print(f"Trades: {len(results['trades'])}")
```

### PerformanceMetrics

**Location:** `src/backtest/performance_metrics.py`

Calculates trading performance metrics.

#### Methods

##### `calculate_metrics(trades: list, initial_capital: float)`

**Parameters:**
- `trades` (list): List of trade dictionaries
- `initial_capital` (float): Starting capital

**Returns:**
- `dict`: Performance metrics including:
  - `total_trades`: Number of trades
  - `win_rate`: % of winning trades
  - `avg_win`: Average winning trade %
  - `avg_loss`: Average losing trade %
  - `profit_factor`: Ratio of profits to losses
  - `sharpe_ratio`: Risk-adjusted returns
  - `max_drawdown`: Largest peak-to-trough decline

---

## Notifications Module

### TelegramBot

**Location:** `src/notifications/telegram_bot.py`

Sends trading notifications via Telegram.

#### Constructor

```python
TelegramBot()
```

Automatically loads configuration from environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

#### Methods

##### `send_message(message: str, parse_mode: str = 'Markdown')`

Sends a message to configured chat.

**Parameters:**
- `message` (str): Message text (supports Markdown)
- `parse_mode` (str): Message formatting mode

**Example:**
```python
bot = TelegramBot()
bot.send_message("Bot started! 🚀")
```

##### `send_entry_alert(direction: str, price: float, entry_reason: str, quality_score: float, tp: float, sl: float)`

Sends trade entry notification.

**Parameters:**
- `direction` (str): 'long' or 'short'
- `price` (float): Entry price
- `entry_reason` (str): Why trade was entered
- `quality_score` (float): Signal quality (0-100)
- `tp` (float): Take profit price
- `sl` (float): Stop loss price

**Example:**
```python
bot.send_entry_alert(
    direction='long',
    price=2500.0,
    entry_reason='RSI oversold + MACD bullish',
    quality_score=75,
    tp=2625.0,
    sl=2481.25
)
```

##### `send_exit_alert(direction: str, entry_price: float, exit_price: float, profit_pct: float, pnl: float, exit_reason: str, hold_time_hours: float)`

Sends trade exit notification.

**Parameters:**
- `direction` (str): Trade direction
- `entry_price` (float): Entry price
- `exit_price` (float): Exit price
- `profit_pct` (float): Profit percentage
- `pnl` (float): Profit/loss in currency
- `exit_reason` (str): Why trade was exited
- `hold_time_hours` (float): Trade duration in hours

##### `send_error_alert(error_type: str, error_message: str)`

Sends error notification.

---

## Reporting Module

### ChartGenerator

**Location:** `src/reporting/chart_generator.py`

Generates interactive trading charts.

#### Methods

##### `create_trading_chart(df: pd.DataFrame, trades: list = None, title: str = 'Trading Chart')`

Creates an interactive Plotly chart.

**Parameters:**
- `df` (DataFrame): Price data with indicators
- `trades` (list, optional): Trade markers to display
- `title` (str): Chart title

**Returns:**
- `plotly.graph_objs.Figure`: Interactive chart object

**Chart Features:**
- Candlestick price chart
- Volume bars
- Technical indicators overlays
- Trade entry/exit markers
- Customizable timeframe

**Example:**
```python
chart_gen = ChartGenerator()
fig = chart_gen.create_trading_chart(
    df=df_with_indicators,
    trades=backtest_trades,
    title='ETH 15m - Iteration 10'
)
fig.show()  # Opens in browser
```

---

## Analysis Module

### OptimalTradeFinder

**Location:** `src/analysis/optimal_trade_finder.py`

Identifies optimal trades in historical data using Maximum Favorable Excursion (MFE) analysis.

#### Constructor

```python
OptimalTradeFinder(min_profit_pct: float = 1.0, min_hold_candles: int = 2)
```

**Parameters:**
- `min_profit_pct` (float): Minimum profit threshold
- `min_hold_candles` (int): Minimum trade duration

#### Methods

##### `find_optimal_trades(df: pd.DataFrame, lookforward_candles: int = 20)`

Analyzes data to find best possible trades.

**Parameters:**
- `df` (DataFrame): Historical price data
- `lookforward_candles` (int): How far to look ahead for exits

**Returns:**
- `list`: Optimal trades with:
  - Entry/exit prices and times
  - Maximum favorable excursion
  - Actual realized profit
  - Hold duration

**Usage:**
Used to establish performance benchmarks and train strategy parameters.

**Example:**
```python
finder = OptimalTradeFinder(min_profit_pct=1.5)
optimal_trades = finder.find_optimal_trades(df, lookforward_candles=30)

print(f"Found {len(optimal_trades)} optimal trades")
print(f"Average profit: {np.mean([t['profit_pct'] for t in optimal_trades]):.2f}%")
```

---

## Optimization Module

### ClaudeOptimizer

**Location:** `src/optimization/claude_optimizer.py`

Uses Claude AI to optimize strategy parameters.

#### Constructor

```python
ClaudeOptimizer(api_key: str = None)
```

**Parameters:**
- `api_key` (str, optional): Anthropic API key (loads from environment if not provided)

#### Methods

##### `optimize_parameters(backtest_results: dict, market_data: pd.DataFrame, current_params: dict)`

Optimizes strategy parameters using AI analysis.

**Parameters:**
- `backtest_results` (dict): Recent backtest results
- `market_data` (DataFrame): Historical market data
- `current_params` (dict): Current strategy parameters

**Returns:**
- `dict`: Optimized parameters with:
  - Updated parameter values
  - Reasoning for changes
  - Expected improvement

**Example:**
```python
optimizer = ClaudeOptimizer()
new_params = optimizer.optimize_parameters(
    backtest_results=latest_results,
    market_data=df_15m,
    current_params=current_strategy_params
)
```

---

## Configuration Files

### strategy_params.json

**Location:** `src/strategy/strategy_params.json`

Contains all strategy parameters.

**Structure:**
```json
{
  "timeframe": "15m",
  "entry_filters": {
    "min_quality_score": 50.0,
    "confluence_score_min": 15,
    "confluence_gap_min": 15,
    "volume_ratio_min": 1.0,
    "volume_types_allowed": ["spike", "elevated", "normal"]
  },
  "exit_strategy": {
    "stop_loss_pct": 0.75,
    "profit_lock_pct": 1.5,
    "take_profit_levels": [5.0]
  },
  "risk_management": {
    "max_position_size_pct": 10.0,
    "max_concurrent_trades": 1,
    "max_daily_trades": 10
  }
}
```

---

## Error Handling

All API methods follow consistent error handling patterns:

```python
try:
    result = client.some_method()
except ConnectionError as e:
    # Network/API connection failed
    print(f"Connection error: {e}")
except ValueError as e:
    # Invalid parameter provided
    print(f"Invalid input: {e}")
except Exception as e:
    # Unexpected error
    print(f"Error: {e}")
    # Log and notify via Telegram if critical
```

---

## Rate Limits and Constraints

### Hyperliquid API
- Rate limit: 1200 requests per minute
- Data availability: Last 2 years maximum
- Supported timeframes: 1m, 5m, 15m, 1h, 4h, 1d

### Telegram API
- Rate limit: 30 messages per second
- Max message length: 4096 characters

---

## Best Practices

### Data Management
1. Always validate data completeness before backtesting
2. Store raw data separately from indicator calculations
3. Use appropriate timeframes for strategy (15m recommended)

### Strategy Development
1. Backtest on at least 6-12 months of data
2. Use walk-forward optimization to prevent overfitting
3. Account for trading costs (fees + slippage)
4. Maintain minimum quality score threshold (≥50)

### Live Trading
1. Start with paper trading mode
2. Use small position sizes initially (5-10%)
3. Monitor closely for first week
4. Set up Telegram notifications
5. Never risk more than you can afford to lose

---

**Last Updated:** October 24, 2025
**Version:** 1.0
**Status:** Complete
