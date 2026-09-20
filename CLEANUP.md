# Automated Cleanup System

## Overview

The application includes an automated cleanup system that manages expired test submissions and game sessions. This helps keep the database clean and ensures student work is properly saved.

## Test Cleanup

### Policy

Tests are automatically cleaned up based on their status:

1. **Live Tests (in_progress)** - Tests started more than 3 hours ago:
   - Automatically submitted to save student work
   - `status` changed to `submitted`
   - `submitted_at` timestamp recorded
   - `time_taken_seconds` calculated

2. **Unstarted Tests** - In-progress tests with no answers older than 3 hours:
   - Deleted from the database
   - These are tests students started but never answered

### How It Works

- **Automatic**: Runs every hour via APScheduler (background task)
- **Manual**: Can be triggered via CLI command
- **Non-destructive for live work**: Tests with answers are always saved, never deleted

### Manual Cleanup

```bash
# Run test cleanup with default 3-hour threshold
python cli.py cleanup-tests

# Run with custom threshold (e.g., 2 hours)
python cli.py cleanup-tests --hours 2
```

### CLI Output

```
✓ Test Cleanup Completed

  Auto-submitted (saved): 5
  Deleted (unstarted):    2
  Total cleaned:          7
  Cutoff time:            2026-08-06T15:30:00
```

## Game Cleanup

### Policy

Game sessions are automatically cleaned based on status and age:

1. **Finished Games** - Deleted after 7 days
2. **Abandoned Games** - Lobby games never started, deleted after 24 hours

### Manual Cleanup

```bash
# Run game cleanup
python cli.py cleanup-games
```

## Configuration

### Scheduler

The background scheduler is configured in `app.py`:

```python
scheduler.add_job(run_test_cleanup, 'interval', hours=1, id='test_cleanup')
```

To modify the cleanup interval:
- Edit the `hours=1` parameter in `app.py`
- Restart the application

### Disable Scheduler (Development)

If you want to disable automatic cleanup during development, comment out the scheduler initialization in `app.py`:

```python
# scheduler.add_job(run_test_cleanup, 'interval', hours=1, id='test_cleanup')
```

## Monitoring

### Check What Will Be Cleaned

Before running cleanup manually, you can query the database to see what will be affected:

```python
from datetime import datetime, timedelta
from models import TestSubmission

cutoff = datetime.utcnow() - timedelta(hours=3)

# Find live tests that will be auto-submitted
live_expired = TestSubmission.query.filter(
    TestSubmission.status == "in_progress",
    TestSubmission.started_at < cutoff
).all()

print(f"Will auto-submit: {len(live_expired)} tests")

# Find unstarted tests that will be deleted
unstarted = [s for s in live_expired if not s.answers]
print(f"Will delete: {len(unstarted)} tests")
```

## Impact on Students

### Positive
- Student work is never lost (live tests auto-saved)
- Prevents abandoned test attempts from cluttering the system
- Ensures clear audit trail (submitted_at timestamp)

### None (No Student Notice Needed)
- Auto-submission is silent (happens in background)
- No notification sent to students
- Tests appear as submitted in their records
- Works just like they manually submitted before time ran out

## Deployment Notes

### Requirements

- APScheduler: `pip install apscheduler`

### Scheduler Behavior

- Starts automatically when app starts
- Runs in background thread
- Does not block web requests
- Survives app reload (restarts with app)

### For Production

For production deployments with multiple app instances:
- Only one instance should run the scheduler (use environment variable)
- Or use a separate cron job to run `python cli.py cleanup-tests`

Example (single scheduler instance):

```python
import os
if os.environ.get('ENABLE_SCHEDULER', '').lower() == 'true':
    scheduler.start()
```

Then in your deployment:
- Set `ENABLE_SCHEDULER=true` on exactly one app instance
- Other instances leave it unset

## Future Enhancements

Possible improvements:
- Configurable thresholds per institution/class
- Logging of all cleanup operations
- Email notification to teachers before cleanup
- Dry-run mode to preview changes
- Retention policies for archived data
