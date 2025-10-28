# COMPREHENSIVE DSP TRADING ARCHITECTURE REVIEW PROMPT

## OBJECTIVE
Perform a deep, thorough analysis of the TradingScalper codebase to determine if it implements a professional real-time DSP-based trading system. Compare the current implementation against the target architecture and identify all gaps, inefficiencies, and areas for improvement.

---

## TARGET ARCHITECTURE REQUIREMENTS

### 1. REAL-TIME DATA ENGINE

#### 1.1 WebSocket Streaming Infrastructure
**What to Check:**
- [ ] WebSocket client implementation for exchange connectivity
- [ ] Connection management (reconnection logic, heartbeat/ping-pong)
- [ ] Message parsing and deserialization (JSON/binary)
- [ ] Error handling and connection recovery
- [ ] Rate limiting and backpressure handling

**Code Patterns to Look For:**
- `websocket`, `websockets`, `ws` libraries
- Async/await patterns with `asyncio`
- Event loops and callback handlers
- Connection state machines

**Questions to Answer:**
1. Is data fetched via WebSocket or REST API polling?
2. If REST polling, what is the polling interval?
3. How is connection failure handled?
4. Is there a queue/buffer for incoming data?

#### 1.2 Multi-Timeframe Candle Aggregation
**What to Check:**
- [ ] Raw tick/1m data aggregation into higher timeframes (5m, 15m, 1h, 4h)
- [ ] OHLCV calculation from raw data
- [ ] Alignment of candle boundaries (proper timestamp handling)
- [ ] Partial candle handling (current incomplete candle)

**Code Patterns to Look For:**
- Timeframe conversion functions (1m → 5m → 15m → 1h → 4h)
- `resample()` or aggregation logic
- Dictionary/array structures indexed by timeframe
- Timestamp normalization (rounding to candle boundaries)

**Questions to Answer:**
1. Are candles aggregated from raw data or fetched separately for each timeframe?
2. How are partial (incomplete) candles handled?
3. Is aggregation incremental (online) or batch-processed?
4. Are all timeframes synchronized properly?

#### 1.3 Data Validation and Gap Handling
**What to Check:**
- [ ] Missing data detection (gap detection between candles)
- [ ] Data quality checks (sanity checks on OHLCV values)
- [ ] Forward-fill or interpolation strategies for gaps
- [ ] Outlier detection and filtering

**Code Patterns to Look For:**
- Timestamp sequence validation
- NaN/None handling
- Data quality metrics (e.g., bid-ask spread checks)
- Logging of data issues

**Questions to Answer:**
1. How are missing candles detected?
2. What happens when data gaps occur?
3. Are there alerts/logging for data quality issues?
4. Is there a mechanism to backfill missing data?

#### 1.4 Efficient Circular Buffers
**What to Check:**
- [ ] Fixed-size ring buffers or deques for streaming data
- [ ] Memory-efficient storage (no unbounded growth)
- [ ] Fast append and retrieval operations
- [ ] Per-timeframe buffer management

**Code Patterns to Look For:**
- `collections.deque(maxlen=N)`
- `numpy` circular buffer implementations
- Fixed-size array structures
- Rolling window implementations

**Questions to Answer:**
1. Are data structures bounded in size?
2. How much historical data is kept in memory?
3. Is old data automatically pruned?
4. What is the memory footprint per symbol?

---

### 2. ADAPTIVE DSP PROCESSOR

#### 2.1 Parallel Multi-Timeframe Processing
**What to Check:**
- [ ] Concurrent processing of multiple timeframes
- [ ] Thread-safe or process-safe implementations
- [ ] Async/await for I/O-bound operations
- [ ] Efficient CPU utilization

**Code Patterns to Look For:**
- `asyncio.gather()`, `asyncio.create_task()`
- `concurrent.futures` (ThreadPoolExecutor, ProcessPoolExecutor)
- `multiprocessing` module usage
- Parallel loops over timeframes

**Questions to Answer:**
1. Are timeframes processed sequentially or in parallel?
2. What parallelization strategy is used (threads, processes, async)?
3. Is there a performance bottleneck in DSP processing?
4. How long does DSP processing take per candle update?

#### 2.2 Online Kalman Filter Updates
**What to Check:**
- [ ] Streaming Kalman filter implementation (incremental updates)
- [ ] State persistence between updates (no full recomputation)
- [ ] Proper state initialization
- [ ] Covariance matrix management

**Code Patterns to Look For:**
- Kalman filter classes with `.update()` or `.predict()` methods
- State vectors and covariance matrices stored as instance variables
- **AVOID:** Full array reprocessing on each new data point
- **AVOID:** Calling `apply_kalman_filter(entire_history)` repeatedly

**Questions to Answer:**
1. Is the Kalman filter applied in streaming mode or batch mode?
2. Does it maintain state between candle updates?
3. Is historical data reprocessed on every update? (BAD)
4. What is the computational complexity per update? O(1) or O(n)?

#### 2.3 Streaming Wavelet Decomposition
**What to Check:**
- [ ] Online wavelet transform (incremental decomposition)
- [ ] Efficient wavelet coefficient updating
- [ ] Multi-resolution analysis across timeframes
- [ ] Proper wavelet reconstruction if needed

**Code Patterns to Look For:**
- Stateful wavelet transform objects
- Windowed wavelet analysis
- **AVOID:** Full `pywt.wavedec()` on entire history each time
- **AVOID:** Batch processing with sliding windows

**Questions to Answer:**
1. Is wavelet decomposition applied incrementally or on full history?
2. Which wavelet family is used (Daubechies, Symlet, Coiflet)?
3. How many decomposition levels are used?
4. Is decomposition synchronized across timeframes?

#### 2.4 Dynamic Parameter Adjustment
**What to Check:**
- [ ] Volatility regime detection (low/medium/high vol states)
- [ ] Market condition classification (trending, ranging, choppy)
- [ ] Adaptive parameter tuning based on regime
- [ ] Feedback loop from performance to parameter adjustment

**Code Patterns to Look For:**
- Volatility estimators (ATR, historical volatility)
- Regime classification logic
- Parameter dictionaries indexed by regime
- Conditional logic switching parameters

**Questions to Answer:**
1. Are DSP parameters fixed or adaptive?
2. How is volatility/regime detected?
3. Which parameters adjust based on market conditions?
4. Is there a learning/optimization loop for parameters?

#### 2.5 Constructive Interference Calculation
**What to Check:**
- [ ] Cross-timeframe coherence measurement
- [ ] Phase alignment detection between timeframes
- [ ] Signal amplification when timeframes agree
- [ ] Signal dampening when timeframes conflict

**Code Patterns to Look For:**
- Cross-correlation between timeframe signals
- Phase difference calculations
- Weighted averaging based on timeframe agreement
- Coherence metrics (e.g., wavelet coherence)

**Questions to Answer:**
1. Are signals from different timeframes compared for coherence?
2. How is "agreement" between timeframes measured?
3. Are signals amplified when timeframes align?
4. Is there a mathematical model for interference (e.g., wave superposition)?

---

### 3. SIGNAL FUSION ENGINE

#### 3.1 Weight Calculation Based on Timeframe Coherence
**What to Check:**
- [ ] Per-timeframe weight assignment
- [ ] Weight calculation based on signal quality/coherence
- [ ] Dynamic weight adjustment over time
- [ ] Normalization of weights (sum to 1.0)

**Code Patterns to Look For:**
- Weight vectors/dictionaries per timeframe
- Coherence-to-weight mapping functions
- Softmax or normalization operations
- Historical performance tracking per timeframe

**Questions to Answer:**
1. How are timeframe weights calculated?
2. Do weights change dynamically or are they fixed?
3. Are longer timeframes weighted more heavily?
4. Is there a mathematical justification for weight calculation?

#### 3.2 Confidence Scoring with Uncertainty Quantification
**What to Check:**
- [ ] Signal confidence metric (0-100% or similar)
- [ ] Uncertainty quantification (variance, standard deviation)
- [ ] Confidence thresholds for trade execution
- [ ] Multiple confidence sources (technical, volume, volatility)

**Code Patterns to Look For:**
- Confidence score calculations
- Standard error or variance tracking
- Bayesian uncertainty estimates
- Threshold-based filtering (e.g., only trade if confidence > 70%)

**Questions to Answer:**
1. Does the system calculate signal confidence?
2. How is uncertainty quantified?
3. Are trades filtered based on confidence levels?
4. Is confidence used for position sizing?

#### 3.3 Multi-Signal Aggregation Logic
**What to Check:**
- [ ] Combination of multiple signal types (trend, momentum, volatility)
- [ ] Voting or consensus mechanisms
- [ ] Signal conflict resolution
- [ ] Hierarchical signal fusion (local → global)

**Code Patterns to Look For:**
- Lists or dictionaries of multiple signals
- Aggregation functions (weighted average, voting, max/min)
- Signal combination algebra (AND/OR logic, multiplicative, additive)
- Priority or hierarchy among signals

**Questions to Answer:**
1. How many distinct signal types are generated?
2. How are conflicting signals resolved?
3. Is there a hierarchy (e.g., higher timeframe overrides lower)?
4. What is the final aggregation formula?

#### 3.4 Entry/Exit Trigger Generation
**What to Check:**
- [ ] Clear entry conditions (long and short)
- [ ] Clear exit conditions (take-profit, stop-loss, signal reversal)
- [ ] Position management logic
- [ ] Risk management integration

**Code Patterns to Look For:**
- Boolean conditions for entry/exit
- State machines for position tracking
- Price level calculations (stop-loss, take-profit)
- Risk-reward ratio calculations

**Questions to Answer:**
1. What are the exact entry conditions?
2. What are the exact exit conditions?
3. How is position sizing determined?
4. How are stop-loss and take-profit levels calculated?

---

## ANALYSIS METHODOLOGY

### Phase 1: Code Discovery
1. List all Python files in the project
2. Identify main entry points and execution flow
3. Map out module dependencies
4. Identify key classes and functions

### Phase 2: Component Mapping
For each of the 3 major components (Data Engine, DSP Processor, Signal Fusion):
1. Find relevant files and functions
2. Extract code snippets showing implementation
3. Classify as: FULLY IMPLEMENTED / PARTIALLY IMPLEMENTED / MISSING
4. Assess streaming vs. batch processing approach

### Phase 3: Gap Analysis
1. Create a checklist of all sub-components
2. Mark each as ✅ (present), ⚠️ (partial), or ❌ (missing)
3. For partial implementations, describe what's missing
4. Identify architectural anti-patterns (e.g., batch reprocessing)

### Phase 4: Performance Assessment
1. Identify potential bottlenecks (file I/O, network, computation)
2. Assess scalability (can it handle multiple symbols?)
3. Evaluate memory efficiency
4. Check for unnecessary recomputation

### Phase 5: Improvement Roadmap
1. Prioritize gaps (critical, high, medium, low priority)
2. Suggest specific code changes with file paths
3. Recommend architectural refactoring if needed
4. Estimate implementation effort (hours/days)

---

## OUTPUT FORMAT

Provide the analysis in the following structure:

```markdown
# DSP TRADING ARCHITECTURE ANALYSIS REPORT

## EXECUTIVE SUMMARY
[Brief overview: % of target architecture implemented, major gaps, overall assessment]

## 1. REAL-TIME DATA ENGINE

### 1.1 WebSocket Streaming Infrastructure
**Status:** ✅ FULLY IMPLEMENTED / ⚠️ PARTIAL / ❌ MISSING
**Files:** [list file paths with line numbers]
**Analysis:**
[Detailed description of what exists, how it works, and any issues]

**Gaps:**
- [List specific missing features]

**Recommendations:**
- [Specific improvements with code suggestions]

[Repeat for 1.2, 1.3, 1.4...]

## 2. ADAPTIVE DSP PROCESSOR
[Same structure as above for 2.1-2.5]

## 3. SIGNAL FUSION ENGINE
[Same structure as above for 3.1-3.4]

## CRITICAL ISSUES
[List of major architectural problems that must be fixed]

## PRIORITY IMPROVEMENTS
### High Priority
1. [Issue + suggested fix + estimated effort]
2. ...

### Medium Priority
[...]

### Low Priority
[...]

## IMPLEMENTATION ROADMAP
[Suggested order of implementation with time estimates]

## APPENDIX: CODE EXAMPLES
[Include relevant code snippets with file paths]
```

---

## CRITICAL EVALUATION CRITERIA

### 🚨 RED FLAGS (Anti-Patterns to Detect)
1. **Batch Reprocessing:** Kalman/wavelet filters applied to entire history on each update
2. **REST API Polling:** Using REST instead of WebSocket for real-time data
3. **No Streaming:** All processing happens on static historical data files
4. **No Multi-Timeframe:** Only single timeframe analysis
5. **Fixed Parameters:** No adaptive parameter adjustment
6. **No Confidence Scoring:** Binary signals without uncertainty quantification
7. **No Coherence Checking:** Timeframes processed independently without cross-validation
8. **Unbounded Memory:** Data structures that grow indefinitely
9. **Sequential Processing:** Timeframes processed one at a time instead of in parallel
10. **No Error Handling:** Missing reconnection logic, gap handling, or validation

### ✅ GREEN FLAGS (Best Practices to Look For)
1. **Streaming Architecture:** Online algorithms with O(1) update complexity
2. **WebSocket Connectivity:** Real-time exchange integration
3. **Incremental Updates:** State maintained between updates
4. **Parallel Processing:** Concurrent multi-timeframe analysis
5. **Adaptive System:** Parameters adjust to market regime
6. **Uncertainty Quantification:** Confidence scores on all signals
7. **Cross-Timeframe Validation:** Coherence checking and interference calculation
8. **Memory Efficiency:** Circular buffers with fixed size
9. **Robust Error Handling:** Reconnection, gap filling, validation
10. **Performance Monitoring:** Logging of processing times and bottlenecks

---

## ADDITIONAL RESEARCH QUESTIONS

### Architecture Questions
1. Is the system designed for backtesting or live trading or both?
2. Can it handle multiple symbols simultaneously?
3. What is the average latency from data arrival to signal generation?
4. Is there a clear separation between data, processing, and execution layers?

### Performance Questions
1. What is the CPU/memory footprint during operation?
2. How many candles per second can be processed?
3. Are there any blocking operations in the main loop?
4. Is there profiling data available?

### Testing Questions
1. Are there unit tests for DSP components?
2. Is there backtesting infrastructure?
3. How is signal quality validated?
4. Are there benchmarks against baseline strategies?

### Operational Questions
1. How is the system deployed (local, cloud, containers)?
2. Is there monitoring and alerting?
3. How are errors and failures logged?
4. Is there a mechanism to pause/resume trading?

---

## INSTRUCTIONS FOR ANALYSIS

1. **Be Thorough:** Check every Python file, especially those related to data, signals, and DSP
2. **Use Code References:** Always include file paths and line numbers (e.g., `data_engine.py:142`)
3. **Show Evidence:** Include code snippets that demonstrate your findings
4. **Be Specific:** Instead of "Kalman filter exists," say "Streaming Kalman filter in `kalman.py:78` with state persistence"
5. **Identify Gaps:** Be explicit about what's missing, not just what exists
6. **Prioritize Issues:** Focus on critical architectural problems first
7. **Suggest Fixes:** Provide actionable recommendations with code examples
8. **Think Like an Engineer:** Consider performance, scalability, maintainability

---

## SUCCESS CRITERIA

The analysis is complete when:
- ✅ Every sub-component (1.1-3.4) has been evaluated
- ✅ Status (✅/⚠️/❌) assigned to each component
- ✅ File paths and line numbers provided for all findings
- ✅ Critical issues identified with severity levels
- ✅ Specific recommendations provided for each gap
- ✅ Implementation roadmap with time estimates created
- ✅ Code examples included for major findings

---

## FINAL NOTE

This is a **deep technical review**, not a surface-level audit. The goal is to understand exactly how the system works at the code level and determine if it matches the target real-time DSP architecture. Be critical, be detailed, and be specific. The output should enable immediate action to close gaps and improve the system.
