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
- ✅ A results JSON file with all details

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
- Make `new Date()` return backdated timestamps
- Make `Date.now()` return backdated timestamps
- Ensure all traces are created with historical timestamps
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
