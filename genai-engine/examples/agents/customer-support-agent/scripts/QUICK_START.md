# Quick Start: Demo Test Harness

## TL;DR

Run 100 inferences with backdated timestamps for demo purposes:

```bash
cd /Users/zfry/git/arthur-engine/genai-engine/examples/agents/customer-support-agent
yarn test:demo
```

This will create:
- ✅ 100 traces in Arthur with timestamps spanning the last 10 days
- ✅ 10 inferences per day (Dec 5 - Dec 14, 2025)
- ✅ Each day's inferences spread from 8am to 8pm
- ✅ Runs 5 inferences in parallel (configurable) for faster completion
- ✅ A results JSON file with all details

**Speed**: With parallel execution, completes in ~10-20 minutes (vs 30-60 minutes sequential)

## What Was Changed

### New Files Created

1. **`scripts/test-harness-demo.ts`** - Main demo harness with timestamp backdating logic
2. **`scripts/run-demo.js`** - Runner script (loads environment variables)
3. **`scripts/DEMO_HARNESS_GUIDE.md`** - Comprehensive guide
4. **`scripts/QUICK_START.md`** - This file

### Modified Files

1. **`package.json`** - Added new scripts:
   - `test:demo` - Run demo harness
   - `test:demo:debug` - Run with debug logging

2. **`scripts/README.md`** - Updated with demo harness documentation

## Key Features

### Timestamp Control

The demo harness uses a `DateOverride` class that temporarily overrides JavaScript's `Date` object to:
- Calculate a time offset between target (backdated) time and real time
- Apply this offset to all `new Date()` and `Date.now()` calls
- Ensure all traces are created with historical timestamps
- **Preserve elapsed time** - span durations are accurate (start and end times are different)
- Automatically restore original Date after each inference

### Data Layout

```
Day 1 (Dec 5):  10 inferences, 8:00am - 7:48pm
Day 2 (Dec 6):  10 inferences, 8:00am - 7:48pm
Day 3 (Dec 7):  10 inferences, 8:00am - 7:48pm
Day 4 (Dec 8):  10 inferences, 8:00am - 7:48pm
Day 5 (Dec 9):  10 inferences, 8:00am - 7:48pm
Day 6 (Dec 10): 10 inferences, 8:00am - 7:48pm
Day 7 (Dec 11): 10 inferences, 8:00am - 7:48pm
Day 8 (Dec 12): 10 inferences, 8:00am - 7:48pm
Day 9 (Dec 13): 10 inferences, 8:00am - 7:48pm
Day 10 (Dec 14): 10 inferences, 8:00am - 7:48pm
Total: 100 inferences
```

### Trace Metadata

Each trace includes:
```json
{
  "name": "demo-run-23-q3",
  "metadata": {
    "demoRun": true,
    "runNumber": 23,
    "dayNumber": 3,
    "questionId": "q3"
  },
  "timestamp": "2024-12-07T09:24:00.000Z"
}
```

## Usage Examples

### Standard Demo Run

```bash
yarn test:demo
```

### With Debug Logging

```bash
yarn test:demo:debug
```

### Resume from a Specific Day

If your terminal closes or you need to stop the script, you can resume from a specific day:

1. Open `scripts/test-harness-demo.ts`
2. Find the `START_FROM_DAY` constant near the top of the `main()` function (around line 411)
3. Change it to the day you want to resume from (e.g., `const START_FROM_DAY = 4;`)
4. Run the script again: `yarn test:demo`

The script will:
- Skip days 1-3 (already completed)
- Start from day 4 and run through day 10
- Use the correct run numbers and timestamps for each day
- Save results to a file named `demo-results-day4-10-{timestamp}.json`

**Example:**
```typescript
// In test-harness-demo.ts, around line 411
const START_FROM_DAY = 4; // <-- Change this number
```

### Adjust Parallel Execution Speed

Control how many inferences run simultaneously:

1. Open `scripts/test-harness-demo.ts`
2. Find the `PARALLEL_INFERENCES` constant (around line 417)
3. Change the value based on your needs:
   - `1-2`: Conservative, good for strict rate limits
   - `3-5`: Recommended default (good balance)
   - `6-10`: Aggressive, only if you have high rate limits

**Example:**
```typescript
// In test-harness-demo.ts, around line 417
const PARALLEL_INFERENCES = 5; // <-- Change this number
```

**Impact on speed:**
- `PARALLEL_INFERENCES = 1`: ~60 minutes (sequential)
- `PARALLEL_INFERENCES = 3`: ~20-25 minutes
- `PARALLEL_INFERENCES = 5`: ~10-15 minutes (recommended)
- `PARALLEL_INFERENCES = 10`: ~8-10 minutes (may hit rate limits)

### Check Progress

Watch the console output for:
- Current day being processed
- Run number (1-100)
- Target timestamp for each inference
- Step-by-step progress (plan, search, draft, review)
- Success/failure status

## Expected Output

### Console

```
Customer Support Agent Demo Test Harness
==========================================
Running 100 inferences with backdated timestamps
10 inferences per day for 10 days

Loading questions from: .../test-questions.json
Loaded 10 test questions
Will run 10 questions x 10 times = 100 total inferences

================================================================================
DAY 1 - Thu Dec 05 2024
================================================================================

================================================================================
[Run 1/100] [Day 1] Processing: q1
Target timestamp: 2024-12-05T08:00:00.000Z
================================================================================
...
```

### Results File

Look for `demo-results-{timestamp}.json` in the `scripts/` directory.

### Arthur Platform

Navigate to your Arthur task to see:
- 100 traces with backdated timestamps
- Traces spread across 10 days
- Each trace fully expanded with all agent calls

## Troubleshooting

### Timestamps not backdated

Make sure you're using the demo harness, not the regular test harness:
- ✅ `yarn test:demo` (backdated)
- ❌ `yarn test:questions` (current time)

### Start and end times are the same (FIXED)

The latest version uses a time offset approach that preserves elapsed time. Your traces should now show:
- ✅ Different start and end times
- ✅ Accurate span durations
- ✅ Backdated to the target date/time

If you see `startTimeUnixNano` = `endTimeUnixNano`, you may be using cached code. Try:
```bash
rm -rf node_modules/.cache
yarn test:demo
```

### Rate limiting

If you hit rate limits, the harness includes a 500ms pause between inferences. You can increase this in `test-harness-demo.ts`.

### Out of memory

The harness processes inferences sequentially to avoid memory issues. If you still encounter problems, reduce TOTAL_RUNS in the script.

## Time Estimate

- **Per inference**: ~3-10 seconds (depends on model and search results)
- **Total time**: 30-60 minutes for 100 inferences
- **Progress**: Live console updates every inference

## Need More Info?

- **Detailed guide**: See `DEMO_HARNESS_GUIDE.md`
- **Script documentation**: See `README.md`
- **Code**: See `test-harness-demo.ts`
