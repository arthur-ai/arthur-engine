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

The demo harness will take **30-60 minutes** to complete, depending on:
- Your API rate limits (OpenAI, Tavily, GitHub)
- Network latency
- Model response times

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

The `DateOverride` class temporarily replaces JavaScript's global `Date` object:

```typescript
class DateOverride {
  constructor(targetDate: Date) {
    // Save original Date
    this.originalDate = Date;
    
    // Create new Date that always returns targetDate
    global.Date = class extends OriginalDate {
      constructor(...args: any[]) {
        if (args.length === 0) {
          super(targetTimestamp);  // Use backdated timestamp
        } else {
          super(...args);
        }
      }
      
      static now() {
        return targetTimestamp;  // Override Date.now()
      }
    }
  }
  
  restore() {
    global.Date = this.originalDate;
  }
}
```

This ensures that:
1. Any `new Date()` call returns the backdated time
2. Any `Date.now()` call returns the backdated timestamp
3. OpenTelemetry spans are created with the backdated start time
4. The original Date is restored after each inference

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

### Rate limiting errors

If you encounter rate limiting:
1. Increase the pause between questions (currently 500ms)
2. Run in smaller batches (modify TOTAL_RUNS)
3. Check your API provider rate limits

### Memory issues

If you see out-of-memory errors:
1. The harness processes questions sequentially to avoid memory spikes
2. Traces are flushed periodically by the BatchSpanProcessor
3. Consider running in smaller batches if needed

## Customization

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
