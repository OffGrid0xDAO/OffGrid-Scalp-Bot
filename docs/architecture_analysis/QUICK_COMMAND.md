# 🚀 Quick Command to Run Analysis

Copy and paste this message to Claude to start the comprehensive analysis:

---

## Full Analysis Command

```
Please perform a comprehensive DSP architecture analysis on my TradingScalper codebase using the framework in docs/architecture_analysis/DSP_ARCHITECTURE_REVIEW_PROMPT.md.

Analyze the following components systematically:

1. REAL-TIME DATA ENGINE
   - WebSocket streaming infrastructure
   - Multi-timeframe candle aggregation
   - Data validation and gap handling
   - Efficient circular buffers

2. ADAPTIVE DSP PROCESSOR
   - Parallel multi-timeframe processing
   - Online Kalman filter updates
   - Streaming wavelet decomposition
   - Dynamic parameter adjustment
   - Constructive interference calculation

3. SIGNAL FUSION ENGINE
   - Weight calculation based on timeframe coherence
   - Confidence scoring with uncertainty quantification
   - Multi-signal aggregation logic
   - Entry/exit trigger generation

For each component:
✅ Determine status: FULLY IMPLEMENTED / PARTIAL / MISSING
✅ Identify file paths and line numbers
✅ Assess if processing is STREAMING or BATCH
✅ List specific gaps and issues
✅ Provide actionable recommendations

Focus especially on detecting these RED FLAGS:
❌ Batch reprocessing (Kalman/wavelet on full history)
❌ REST API polling instead of WebSocket
❌ No multi-timeframe analysis
❌ Fixed parameters (no adaptation)
❌ No confidence scoring
❌ Sequential processing (no parallelization)
❌ Unbounded memory growth

Provide:
1. Executive summary with completion %
2. Component-by-component detailed analysis
3. Critical issues list (prioritized)
4. Implementation roadmap with time estimates
5. Code examples showing current state and recommendations

Be thorough, specific, and include file:line references for all findings.
```

---

## Quick Critical-Issues-Only Command

If you just want to know what's broken:

```
Analyze my TradingScalper codebase for critical architectural issues based on real-time DSP trading system requirements.

Focus only on:
❌ RED FLAGS: Batch processing, REST polling, no streaming, single timeframe
❌ CRITICAL GAPS: Missing components that prevent real-time operation
❌ TOP 5 PRIORITIES: Most impactful improvements with effort estimates

Be brief but specific with file paths and line numbers.
```

---

## Targeted Component Analysis

To analyze just one component:

```
Analyze the [COMPONENT NAME] in my TradingScalper codebase:

[Replace COMPONENT NAME with one of:]
- Real-Time Data Engine
- Adaptive DSP Processor
- Signal Fusion Engine

Determine:
1. What exists vs what's missing
2. Is it streaming or batch?
3. File paths and line numbers
4. Top 3 improvements needed

Be specific and include code examples.
```

---

## Verification Command (After Making Changes)

After implementing improvements:

```
I've implemented [DESCRIBE CHANGES] in [FILE PATHS].

Please verify:
1. Does this now match the DSP architecture requirements?
2. Is it properly streaming/online (not batch)?
3. Are there any remaining issues?
4. What should I test to validate correctness?

Reference the requirements in docs/architecture_analysis/DSP_ARCHITECTURE_REVIEW_PROMPT.md
```

---

## Progress Check Command

To see how much you've completed:

```
Based on the DSP architecture requirements in docs/architecture_analysis/DSP_ARCHITECTURE_REVIEW_PROMPT.md:

1. What % of the target architecture is currently implemented?
2. Which components are complete vs partial vs missing?
3. What are the next 3 most important improvements?
4. How much total effort (hours/days) to reach production-ready?

Provide a concise progress report.
```

---

## Copy-Paste Ready Commands

**For First-Time Analysis:**
```
Read docs/architecture_analysis/DSP_ARCHITECTURE_REVIEW_PROMPT.md and perform the complete analysis on my TradingScalper codebase. Generate the full report as specified in the document.
```

**For Quick Assessment:**
```
Quick assessment: Does my TradingScalper codebase use streaming DSP or batch processing? List top 3 critical issues.
```

**For Specific Component:**
```
Analyze only the Kalman filter implementation. Is it streaming or batch? Show code examples and how to fix if needed.
```

---

## Tips for Best Results

1. **Be Specific**: Point Claude to specific files if you know where to look
   ```
   Focus your analysis on these files:
   - data_fetcher.py
   - signal_generator.py
   - kalman_filter.py
   ```

2. **Ask for Code Examples**: Always request before/after code
   ```
   For each issue found, show:
   1. Current code (with file:line)
   2. Recommended fix (with code example)
   ```

3. **Request Priorities**: Get actionable next steps
   ```
   Rank all improvements by:
   - Critical (system won't work)
   - High (major performance/correctness impact)
   - Medium (nice to have)
   - Low (polish)
   ```

4. **Iterative Analysis**: Start broad, then drill down
   ```
   First pass: Executive summary only
   Second pass: Deep dive on critical issues
   Third pass: Detailed recommendations for each component
   ```

---

## Example Workflow

### Session 1: Discovery
```
1. "Read DSP_ARCHITECTURE_REVIEW_PROMPT.md and give me an executive summary
    of what needs to be analyzed"

2. "Now run the full analysis focusing on critical issues first"

3. "For the top 3 critical issues, show me exactly what code needs to change"
```

### Session 2: Implementation
```
1. "I'm going to fix [ISSUE]. Guide me step-by-step with code examples"

2. [After implementing] "Review my changes in [FILE]. Did I implement it correctly?"

3. "What should I test to verify this fix works properly?"
```

### Session 3: Validation
```
1. "Re-run the analysis on [COMPONENT]. Is it now compliant?"

2. "What's my new completion percentage?"

3. "What should I work on next?"
```

---

## Common Follow-Up Questions

After the initial analysis, ask:

- "Which issue would give me the biggest performance improvement?"
- "Show me how to convert my batch Kalman filter to streaming mode"
- "How do I implement multi-timeframe coherence checking?"
- "What's the proper architecture for real-time WebSocket data handling?"
- "How should I structure circular buffers for each timeframe?"
- "Explain constructive interference between timeframes with an example"

---

**Save this file for quick reference whenever you need to analyze or improve your codebase!**
