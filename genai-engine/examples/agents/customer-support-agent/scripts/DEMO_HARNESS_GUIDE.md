# Demo Test Harness Guide

## Overview

The demo test harness is designed to create realistic historical data for demonstrations and presentations. It runs 100 inferences through the Customer Support Agent with backdated timestamps, creating a dataset that spans 10 days with 10 inferences per day.

## What It Does

### Timestamp Backdating

The demo harness uses a clever `DateOverride` class to temporarily override JavaScript's `Date` object during each inference run. This ensures that:

1. **All traces have backdated timestamps**: When traces are created and sent to Arthur, they will have timestamps from the past
2. **Realistic time distribution**: Inferences are spread across each day from 8am to 8pm
3. **Consistent timing**: All operations within a single inference (agent calls, tool executions) share the same backdated timestamp

### Data Distribution

- **Total inferences**: 100
- **Duration**: 10 days (starting from today and going backwards)
- **Per day**: 10 inferences
- **Time spread**: Each day's inferences are spread across 12 hours (8am - 8pm), 72 minutes apart

### Timeline Example

If you run the demo on December 14, 2025:
- **Day 1** (Dec 5): 10 inferences from 8:00am - 7:48pm
- **Day 2** (Dec 6): 10 inferences from 8:00am - 7:48pm
- ...
- **Day 10** (Dec 14): 10 inferences from 8:00am - 7:48pm

## How to Run

### Quick Start

```bash
yarn test:demo
```

### With Debug Logging

```bash
yarn test:demo:debug
```

### Expected Duration

The demo harness uses **parallel execution** to speed up the process:

- **With parallelization (default, 5 concurrent)**: ~10-20 minutes
- **Sequential execution (1 concurrent)**: ~30-60 minutes

Duration depends on:
- Your API rate limits (OpenAI, Tavily, GitHub)
- Network latency
- Model response times
- Number of parallel inferences (configurable)

## What Gets Created

### 1. Traces in Arthur

Each of the 100 inferences creates a complete trace in Arthur with:
- **Root span name**: `demo-run-{runNumber}-{questionId}` (e.g., `demo-run-23-q3`)
- **Backdated timestamp**: From the past 10 days
- **Metadata**:
  ```json
  {
    "demoRun": true,
    "runNumber": 23,
    "dayNumber": 3,
    "questionId": "q3"
  }
  ```
- **Full agent execution tree**: All nested spans for plan, search, draft, and review agents

### 2. Results JSON File

A file named `demo-results-{timestamp}.json` containing detailed results:

```json
[
  {
    "questionId": "q1",
    "question": "What metrics does the Arthur Platform provide?",
    "category": "general",
    "answer": "...",
    "sources": ["..."],
    "completeness": "complete",
    "metadata": {
      "plan": "...",
      "searchesConducted": {
        "docs": true,
        "code": false
      }
    },
    "timestamp": "2024-12-05T08:00:00.000Z",
    "durationMs": 5432,
    "runNumber": 1,
    "dayNumber": 1
  },
  // ... 99 more results
]
```

### 3. Console Output

The harness provides detailed progress logging:

```
================================================================================
DAY 1 - Wed Dec 05 2024
================================================================================

================================================================================
[Run 1/100] [Day 1] Processing: q1
Target timestamp: 2024-12-05T08:00:00.000Z
================================================================================
Step 1: Creating plan...
Plan: Search documentation and examples
Needs docs: true, Needs code: false

Steps 2-3: Executing searches...
  - Searching docs with query: "Arthur Platform metrics"
  ✓ Docs search completed: 3 sources

Step 4: Drafting response...
Draft confidence: high

Step 5: Reviewing and finalizing...

✓ Completed in 5432ms
Completeness: complete
Sources: 3
```

## Use Cases

### 1. Demo Preparation

Create a realistic dataset showing:
- Agent performance over time
- Daily usage patterns
- Response quality trends
- Source utilization

### 2. Feature Testing

Test Arthur Platform features that require historical data:
- Date-based filtering
- Time-series analytics
- Trend visualization
- Cohort analysis

### 3. Presentations

Show stakeholders:
- Agent behavior across multiple days
- Consistency in response quality
- Search pattern distribution
- Performance metrics over time

## Technical Details

### How Timestamp Override Works

The `DateOverride` class temporarily replaces JavaScript's global `Date` object with a version that applies a time offset:

```typescript
class DateOverride {
  constructor(targetDate: Date) {
    // Calculate time offset: target time - real time
    const realNow = Date.now();
    const targetTimestamp = targetDate.getTime();
    this.timeOffset = targetTimestamp - realNow;
    
    // Create new Date that applies the offset
    global.Date = class extends OriginalDate {
      constructor(...args: any[]) {
        if (args.length === 0) {
          // Apply offset to current real time
          super(OriginalDate.now() + timeOffset);
        } else {
          super(...args);
        }
      }
      
      static now() {
        // Apply offset to current real time
        return OriginalDate.now() + timeOffset;
      }
    }
  }
  
  restore() {
    global.Date = this.originalDate;
  }
}
```

This ensures that:
1. Any `new Date()` call returns the backdated time + elapsed real time
2. Any `Date.now()` call returns the backdated timestamp + elapsed real time
3. OpenTelemetry spans are created with backdated start times
4. **Time progresses naturally** - span end times correctly reflect elapsed duration
5. The original Date is restored after each inference

**Example**: If the target date is Dec 5 at 8:00am and an agent call takes 2 seconds:
- Span start time: Dec 5 at 8:00:00am (backdated)
- Span end time: Dec 5 at 8:00:02am (backdated + 2 seconds elapsed)
- Duration: 2 seconds (preserved correctly)

### Why This Works

The OpenTelemetry tracing infrastructure used by the Arthur exporter relies on `Date.now()` and `new Date()` to set span timestamps. By overriding these at the moment each inference starts, we ensure that:

- Root span gets the backdated start time
- All child spans (agent calls, tool executions) inherit the same timeframe
- The entire trace tree has consistent, backdated timestamps
- Arthur receives and stores traces with the historical timestamps

### Safety

- The Date override is **scoped to each inference** using try/finally blocks
- The original Date is **always restored** after each run
- No permanent modifications to the Date object
- No impact on subsequent inferences or the rest of the application

## Troubleshooting

### Traces appear with current timestamps

If traces show up in Arthur with current timestamps instead of backdated ones, check:
1. The DateOverride is being created before `aiTracing.startSpan()`
2. The DateOverride is not being restored too early (should be in finally block)
3. No other code is creating Date instances before the override

### Start and end times are the same

**Fixed in latest version!** If you see traces where `startTimeUnixNano` equals `endTimeUnixNano`, you're using an older version that froze time instead of applying an offset. The current implementation:
- Uses a time offset approach (target time - real time)
- Applies the offset to all Date operations
- Allows time to progress naturally during execution
- Results in accurate span durations with different start/end times

Example of correct timestamps:
```json
{
  "startTimeUnixNano": "1733400000000000000",  // Dec 5, 8:00:00am
  "endTimeUnixNano": "1733400002500000000",    // Dec 5, 8:00:02.5am
  "duration": "2500ms"
}
```

### Rate limiting errors

If you encounter rate limiting errors from OpenAI, Tavily, or GitHub:

1. **Reduce concurrency**: Lower `PARALLEL_INFERENCES` from 5 to 2 or 3
2. **Add delays**: Increase the pause between days (currently 1000ms)
3. **Check your limits**: Verify your API tier and rate limits
4. **Resume later**: Use `START_FROM_DAY` to continue after a cooldown period

Example rate limit-friendly configuration:
```typescript
const START_FROM_DAY = 1;
const PARALLEL_INFERENCES = 2;  // Reduced from 5
```

If errors persist, try sequential execution:
```typescript
const PARALLEL_INFERENCES = 1;  // One at a time
```

### Memory issues

If you see out-of-memory errors:
1. The harness processes questions sequentially to avoid memory spikes
2. Traces are flushed periodically by the BatchSpanProcessor
3. Consider running in smaller batches if needed

## Parallel Execution

The demo harness uses a **Semaphore pattern** to run multiple inferences concurrently while respecting rate limits.

### How It Works

1. **Days run sequentially**: Each day's 10 inferences complete before moving to the next day
2. **Questions run in parallel**: Within each day, multiple questions run concurrently
3. **Concurrency control**: A semaphore limits how many inferences run simultaneously
4. **Progress tracking**: Real-time updates show completion rate and speed

### Benefits

- **Faster completion**: 3-6x speedup compared to sequential execution
- **Rate limit protection**: Configurable concurrency prevents API throttling
- **Better resource usage**: Maximizes throughput while waiting for API responses
- **Graceful handling**: Failed inferences don't block others

### Console Output

You'll see progress updates like:
```
================================================================================
DAY 4 - Fri Dec 08 2024
================================================================================
  ✓ [31/100] Run #31 completed (15.3s elapsed, 121.6 runs/min)
  ✓ [32/100] Run #32 completed (17.8s elapsed, 107.9 runs/min)
  ✓ [33/100] Run #33 completed (19.2s elapsed, 103.1 runs/min)
  ✓ [34/100] Run #34 completed (22.1s elapsed, 92.3 runs/min)
  ✓ [35/100] Run #35 completed (23.5s elapsed, 89.4 runs/min)
  ...
```

## Customization

### Adjust Concurrency

Edit `test-harness-demo.ts` near the top of the `main()` function:

```typescript
const PARALLEL_INFERENCES = 5;  // Number of concurrent inferences
```

**Recommendations:**
- **Conservative (1-2)**: Use if you have strict rate limits or want to be safe
- **Recommended (3-5)**: Good balance between speed and reliability
- **Aggressive (6-10)**: Only if you have high rate limits and want maximum speed

**Trade-offs:**
- Higher concurrency = faster completion but more risk of rate limiting
- Lower concurrency = slower but more reliable
- Monitor the runs/min rate to find your optimal setting

### Resume from a Specific Day

If your script is interrupted, you can resume from a specific day without re-running everything:

Edit `test-harness-demo.ts` near the top of the `main()` function:

```typescript
const START_FROM_DAY = 4;  // Resume from day 4 (skips days 1-3)
```

The script will automatically:
- Calculate the correct run numbers (e.g., day 4 starts at run #31)
- Use the correct timestamps for each day
- Save results with the day range in the filename
- Display a warning that you're resuming from a later day

**Use cases:**
- Terminal closed unexpectedly
- Rate limit errors forced you to stop
- Need to split the demo run across multiple sessions
- Only want to generate data for specific days

### Change Number of Days

Edit `test-harness-demo.ts`:

```typescript
const TOTAL_DAYS = 10;  // Change to desired number of days
```

### Change Inferences Per Day

```typescript
const RUNS_PER_DAY = 10;  // Change to desired number per day
```

### Change Time Range

```typescript
const targetDateTime = new Date(targetDate);
targetDateTime.setHours(8);  // Start hour (8am)
targetDateTime.setMinutes(questionIdx * 72);  // 72 mins = 12 hour spread
```

### Change Question Order

The demo cycles through the 10 questions in `test-questions.json`. To randomize or change the order, modify:

```typescript
const question = questions[questionIdx % questions.length];
```

## Next Steps

After running the demo harness:

1. **View traces in Arthur**: Navigate to the Arthur trace viewer to see your backdated traces
2. **Analyze trends**: Use Arthur's analytics to see patterns over the 10-day period
3. **Test filters**: Try filtering by date, day of week, or time of day
4. **Export data**: Use the results JSON file for additional analysis or reporting
