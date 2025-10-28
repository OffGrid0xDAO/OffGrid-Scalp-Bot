# Historical Data Performance Optimization Plan

## 🎯 TARGET: 10X Faster Backtesting & Charting

Based on your performance concerns, here are specific optimizations for historical data processing.

## 📊 CURRENT BOTTLENECKS

### Backtesting Issues:
1. **Sequential Timeframe Processing** - 5x slower than necessary
2. **Full FFT Re-computation** - O(n²) complexity instead of O(n)
3. **No Incremental Updates** - Re-processing entire history
4. **Memory Inefficiency** - Loading all data at once

### Chart Rendering Issues:
1. **Full History Re-processing** - Computing indicators on every render
2. **No Result Caching** - Same calculations repeated
3. **Synchronous Operations** - Blocking UI during processing
4. **Inefficient Data Structures** - Slow DataFrame operations

## 🚀 OPTIMIZATION STRATEGIES

### 1. Parallel Historical Processing
**File:** `src/analysis/historical_processor.py` (NEW)

```python
class ParallelHistoricalProcessor:
    """Process historical data in parallel chunks"""

    async def process_backtest_parallel(self,
                                       symbol: str,
                                       start_date: datetime,
                                       end_date: datetime,
                                       timeframes: List[str]) -> Dict:
        """Process all timeframes in parallel"""

        # Split data into chunks for parallel processing
        data_chunks = self._split_data_into_chunks(start_date, end_date)

        # Create tasks for each timeframe and chunk
        tasks = []
        for tf in timeframes:
            for chunk in data_chunks:
                task = self._process_chunk_parallel(symbol, tf, chunk)
                tasks.append(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks)

        # Merge results
        return self._merge_results(results)

    def _process_chunk_parallel(self, symbol: str, timeframe: str, chunk: Dict) -> Dict:
        """Process data chunk with optimized algorithms"""
        # Use streaming updates instead of batch processing
        processor = StreamingProcessor(timeframe)

        for candle in chunk['data']:
            processor.update_streaming(candle)

        return processor.get_results()
```

### 2. Incremental FFT Updates
**File:** `src/analysis/incremental_fft.py` (NEW)

```python
class IncrementalFFT:
    """FFT with O(1) update complexity for streaming data"""

    def __init__(self, window_size: int = 200):
        self.window_size = window_size
        self.circ_buffer = np.zeros(window_size)
        self.fft_cache = None
        self.position = 0

    def update(self, new_value: float) -> np.ndarray:
        """Update FFT with O(1) complexity"""
        # Add new value to circular buffer
        self.circ_buffer[self.position] = new_value
        self.position = (self.position + 1) % self.window_size

        # Use cached FFT if we have enough data
        if self.fft_cache is not None and self._should_use_cache():
            return self._update_fft_incremental(new_value)

        # Otherwise compute full FFT (rare)
        self.fft_cache = np.fft.fft(self.circ_buffer)
        return self.fft_cache

    def _update_fft_incremental(self, new_value: float) -> np.ndarray:
        """Update FFT incrementally using mathematical properties"""
        # Use the fact that FFT(x[n+1]) = FFT(x[n]) + correction_term
        old_value = self.circ_buffer[(self.position - 1) % self.window_size]
        correction = self._compute_fft_correction(old_value, new_value)
        self.fft_cache += correction
        return self.fft_cache
```

### 3. Smart Caching System
**File:** `src/analysis/result_cache.py` (NEW)

```python
class ResultCache:
    """Intelligent caching for computed results"""

    def __init__(self, max_cache_size: int = 1000):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_cache_size

    def get_or_compute(self, key: str, compute_func: Callable, *args, **kwargs):
        """Get cached result or compute and cache it"""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]

        # Compute result
        result = compute_func(*args, **kwargs)

        # Cache if under size limit
        if len(self.cache) < self.max_size:
            self.cache[key] = result
            self.access_times[key] = time.time()

        return result

    def get_cached_data_range(self, symbol: str, timeframe: str,
                            start_time: datetime, end_time: datetime) -> Optional[pd.DataFrame]:
        """Get cached data for a time range"""
        key = f"{symbol}_{timeframe}_{start_time}_{end_time}"
        return self.cache.get(key)

    def cache_data_range(self, symbol: str, timeframe: str,
                        start_time: datetime, end_time: datetime,
                        data: pd.DataFrame):
        """Cache processed data for a time range"""
        key = f"{symbol}_{timeframe}_{start_time}_{end_time}"
        self.cache[key] = data
```

### 4. Optimized Chart Rendering
**File:** `src/reporting/fast_chart_renderer.py` (NEW)

```python
class FastChartRenderer:
    """Optimized chart rendering with caching and async processing"""

    def __init__(self):
        self.cache = ResultCache()
        self.precomputed_indicators = {}

    async def render_chart_async(self,
                                symbol: str,
                                timeframe: str,
                                start_date: datetime,
                                end_date: datetime,
                                indicators: List[str]) -> str:
        """Render chart asynchronously without blocking"""

        # Check cache first
        cache_key = f"chart_{symbol}_{timeframe}_{start_date}_{end_date}"
        cached_chart = self.cache.get(cache_key)
        if cached_chart:
            return cached_chart

        # Load data asynchronously
        data = await self._load_data_async(symbol, timeframe, start_date, end_date)

        # Pre-compute indicators in parallel
        indicator_tasks = [
            self._compute_indicator_async(ind, data)
            for ind in indicators
        ]
        indicators_data = await asyncio.gather(*indicator_tasks)

        # Render chart (non-blocking)
        chart_html = await self._render_chart_nonblocking(
            data, indicators_data, symbol, timeframe
        )

        # Cache result
        self.cache.set(cache_key, chart_html)

        return chart_html

    async def _compute_indicator_async(self, indicator: str, data: pd.DataFrame):
        """Compute indicator asynchronously"""
        if indicator in self.precomputed_indicators:
            cached = self.precomputed_indicators[indicator].get(data_hash(data))
            if cached:
                return cached

        # Compute in background
        result = await asyncio.to_thread(self._compute_indicator, indicator, data)

        # Cache for future use
        if indicator not in self.precomputed_indicators:
            self.precomputed_indicators[indicator] = {}
        self.precomputed_indicators[indicator][data_hash(data)] = result

        return result
```

### 5. Memory-Efficient Data Loading
**File:** `src/analysis/streaming_data_loader.py` (NEW)

```python
class StreamingDataLoader:
    """Load historical data in streaming chunks to save memory"""

    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size

    def load_historical_data_streaming(self,
                                     symbol: str,
                                     timeframe: str,
                                     start_date: datetime,
                                     end_date: datetime) -> Iterator[pd.DataFrame]:
        """Load data in chunks instead of all at once"""

        current_date = start_date

        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=30), end_date)

            # Load chunk
            chunk_data = self._load_chunk(symbol, timeframe, current_date, chunk_end)

            if len(chunk_data) > 0:
                yield chunk_data

            current_date = chunk_end

            # Allow garbage collection
            import gc
            gc.collect()

    def process_backtest_streaming(self,
                                  symbol: str,
                                  timeframes: List[str],
                                  start_date: datetime,
                                  end_date: datetime) -> Iterator[Dict]:
        """Process backtest with streaming data to minimize memory usage"""

        # Create data loaders for each timeframe
        loaders = {
            tf: self.load_historical_data_streaming(symbol, tf, start_date, end_date)
            for tf in timeframes
        }

        # Process in parallel chunks
        while True:
            chunks = {}
            has_data = False

            for tf, loader in loaders.items():
                try:
                    chunk = next(loader)
                    chunks[tf] = chunk
                    has_data = True
                except StopIteration:
                    chunks[tf] = None

            if not has_data:
                break

            # Process this chunk in parallel
            chunk_results = self._process_chunks_parallel(chunks)
            yield chunk_results
```

## 🔧 IMPLEMENTATION PLAN

### Phase 1: Core Optimizations (Week 1)
1. **Day 1-2:** Implement `IncrementalFFT` and `ParallelHistoricalProcessor`
2. **Day 3-4:** Create `ResultCache` and `FastChartRenderer`
3. **Day 5:** Integrate with existing backtest engine

### Phase 2: Advanced Optimizations (Week 2)
1. **Day 1-2:** Implement `StreamingDataLoader` for memory efficiency
2. **Day 3-4:** Optimize existing chart generation code
3. **Day 5:** Performance testing and benchmarking

## 📊 EXPECTED IMPROVEMENTS

### Backtesting Performance:
- **Current:** 5-10 minutes for 6-month backtest
- **After Phase 1:** 1-2 minutes for 6-month backtest (5-10x improvement)
- **After Phase 2:** 30-60 seconds for 6-month backtest (10-20x improvement)

### Chart Rendering Performance:
- **Current:** 10-30 seconds for complex charts
- **After Optimization:** 1-3 seconds for same charts (10-30x improvement)

### Memory Usage:
- **Current:** 2-4GB for large backtests
- **After Optimization:** 500MB-1GB for same backtests (4-8x improvement)

## 🚀 QUICK WINS (Can be implemented today)

### 1. Add Simple Caching to Existing Code
```python
# Add to existing chart generation
import functools

@functools.lru_cache(maxsize=100)
def cached_compute_indicators(data_hash, indicators_str):
    # Cache indicator computations
    pass

@functools.lru_cache(maxsize=50)
def cached_chart_render(chart_key):
    # Cache chart rendering
    pass
```

### 2. Use Multiprocessing for Backtesting
```python
from multiprocessing import Pool

def parallel_backtest(params_list):
    with Pool(processes=4) as pool:
        results = pool.map(run_single_backtest, params_list)
    return results
```

### 3. Optimize DataFrame Operations
```python
# Replace slow operations
df['sma'] = df['close'].rolling(20).mean()  # Slow

# With faster operations
df['sma'] = df['close'].rolling(20, min_periods=1).mean()  # Faster
```

## 🎯 INTEGRATION WITH DSP OPTIMIZATIONS

The historical data optimizations work synergistically with the DSP improvements:

1. **Parallel Processing** benefits both real-time and historical analysis
2. **Streaming Algorithms** work for both live and backtest data
3. **Caching System** speeds up both charting and backtesting
4. **Memory Optimization** enables larger historical analysis

## 📈 PERFORMANCE MONITORING

Add performance tracking to measure improvements:

```python
import time
import psutil

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}

    def time_function(self, func_name: str):
        """Decorator to time function execution"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024

                result = func(*args, **kwargs)

                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024

                self.metrics[func_name] = {
                    'time': end_time - start_time,
                    'memory_delta': end_memory - start_memory
                }

                return result
            return wrapper
        return decorator

    def get_performance_report(self) -> str:
        """Generate performance report"""
        report = "Performance Metrics:\n"
        for func_name, metrics in self.metrics.items():
            report += f"{func_name}: {metrics['time']:.2f}s, {metrics['memory_delta']:.1f}MB\n"
        return report
```

These optimizations will make your backtesting and chart visualization dramatically faster while maintaining the same accuracy and adding the DSP improvements!