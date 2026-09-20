# Student Feedback with Prompt Caching

This system provides AI-generated feedback to students on quiz answers using **prompt caching** to reduce token usage by up to 90%.

## How It Works

### The Problem
Each time you generate feedback for a student answer, the system sends:
- A stable **system prompt** (same for all students) — "Tell the student how to improve..."
- Variable **student data** (different each time) — their answer, the question, marking guide

Without caching, you pay full price for the system prompt every time. With 100 students, that's 100× the system prompt cost.

### The Solution: Prompt Caching
- **First request**: Write system prompt to cache (costs 1.25× input tokens)
- **Requests 2-300**: Read system prompt from cache (costs 0.1× input tokens)
- **Break-even**: After 2 requests, you've saved tokens
- **Savings**: With 10+ students, you save ~15-20% on total input tokens

### Cache Details
- **Duration**: 5 minutes (ephemeral cache)
- **Reusable**: Survives across the same quiz class
- **Cost**: First request pays the write cost; subsequent requests get 90% discount on that content

## Usage

### Basic Usage (Automatic)
The feedback system is integrated into `quiz_routes.py`. When a student submits a quiz answer, feedback is automatically generated with caching:

```python
# In quiz_routes.py
from student_feedback import get_improvement_feedback, get_correction_feedback

# For correct answers: suggest improvements
feedback, cache_stats = get_improvement_feedback(
    question_text="What is photosynthesis?",
    markscheme="Plants use sunlight, water, and CO2...",
    answer_text="Plants make food using light and water.",
    log_cache_stats=True  # Logs cache hits
)

# For incorrect answers: explain the correction
feedback, cache_stats = get_correction_feedback(
    question_text="What is photosynthesis?",
    markscheme="Plants use sunlight, water, and CO2...",
    answer_text="Plants breathe using sunlight.",
    log_cache_stats=True
)
```

### Monitoring Cache Performance
Cache hits are automatically logged. Check your logs for:
```
INFO: Cache hit! Saved 1250 tokens (82% from cache)
INFO: Cache written: 1540 tokens (5-min ephemeral cache)
```

### Batch Statistics
To track efficiency across multiple students:

```python
from student_feedback import get_batch_feedback_stats

feedback_results = [
    {"cache_stats": {...}},  # result from get_improvement_feedback
    {"cache_stats": {...}},  # another result
    # ... more results
]

stats = get_batch_feedback_stats(feedback_results)
print(f"Cache efficiency: {stats['average_efficiency_pct']:.1f}%")
print(f"Tokens saved: {stats['total_cached_read_tokens']}")
```

## Demo

Run the example to see the system in action:

```bash
python example_student_feedback.py
```

This generates feedback for 6 student answers (3 correct, 3 incorrect) and shows:
- Individual feedback for each answer
- Cache statistics for each request
- Batch statistics showing overall efficiency

Expected output:
```
Total requests: 6
Cache hits: 5
Tokens from cache: 5250
Tokens written to cache: 1250
Average efficiency: 81.8% from cache
```

## Implementation Details

### Files

1. **student_feedback.py** — Core module with caching implementation
   - `get_improvement_feedback()` — Feedback for correct answers
   - `get_correction_feedback()` — Feedback for incorrect answers
   - `get_batch_feedback_stats()` — Aggregate cache statistics

2. **quiz_routes.py** — Updated to use the cached system
   - `claude_improvement_feedback()` now uses prompt caching

3. **example_student_feedback.py** — Demo script
   - Shows both improvement and correction feedback
   - Displays cache statistics
   - Demonstrates batch reporting

### Cache Architecture

```
┌─────────────────────────────────────────┐
│         System Prompt (Stable)          │ ← Cached with 5-min TTL
│  "You give students feedback on..."     │   Cost: 1st req = 1.25×
├─────────────────────────────────────────┤   Cost: 2-300 reqs = 0.1×
│  Question + Markscheme + Answer (Var)   │ ← Not cached
│  "What is photosynthesis? ..."          │   Cost: every request = 1×
├─────────────────────────────────────────┤
│              Response                   │
│  "Consider explaining the role of..."   │
└─────────────────────────────────────────┘
```

### Token Economics

For a class of 30 students, each answering 5 questions (150 total answers):

| Scenario | System Tokens | Per-Answer Tokens | Total Input | Savings |
|----------|--------------|-------------------|-------------|---------|
| **No cache** | 150 × 1540 | 150 × 500 | 306,000 | — |
| **With cache** | 1540 + 149 × 154 | 150 × 500 | 99,266 | **68%** |

(Numbers assume ~1540 tokens for system prompt, ~500 per answer)

## Monitoring & Optimization

### Check Cache Hit Rate
Monitor your application logs for cache efficiency:
```
# High cache efficiency (good)
Cache hit! Saved 1250 tokens (82% from cache)

# Low cache efficiency (something's off)
Cache written: 1540 tokens (no prior cache)
```

### If Cache Isn't Working
Cache misses happen when the system prompt changes. Check:
- Is the system prompt identical between requests?
- Are you using the same model?
- Is the timestamp < 5 minutes?

### Scaling Up
For large batches (100+ students):
- Consider using 1-hour TTL instead of 5 minutes:
  ```python
  cache_control={"type": "ephemeral", "ttl": "1h"}
  ```
- Monitor batch statistics to confirm cache efficiency
- Log to a monitoring system for dashboard visibility

## Troubleshooting

### "Cache hit but tokens show as 0"
This means the cache prefix was too short (<1024 tokens). The system prompt is slightly under the minimum in some models. Not a problem — it just means that particular request wasn't cached, but the next one will be.

### "No cache hits after multiple requests"
Check:
1. Is `ANTHROPIC_API_KEY` set?
2. Are you using a model that supports caching (Opus 4.6+, Sonnet 4.6+)?
3. Is the system prompt identical?
4. Did 5+ minutes pass since the first request?

### "High cache cost but low hit rate"
The cache write cost (1.25×) outweighs benefit if you don't get multiple hits. This is normal for:
- Single one-off requests
- Requests with different system prompts

Just let the cache expire and it won't be a problem next batch.

## API Reference

### get_improvement_feedback()
```python
feedback, cache_stats = get_improvement_feedback(
    question_text: str,
    markscheme: str,
    answer_text: str,
    log_cache_stats: bool = True
) -> Tuple[Optional[str], dict]
```

**Returns:**
- `feedback`: Markdown text with **bold** improvement suggestions, or None
- `cache_stats`: Dict with:
  - `cache_creation_tokens`: Tokens written to cache
  - `cache_read_tokens`: Tokens served from cache
  - `efficiency_pct`: % of tokens from cache
  - `uncached_input_tokens`: Full-price tokens
  - `output_tokens`: Response tokens

### get_correction_feedback()
```python
feedback, cache_stats = get_correction_feedback(
    question_text: str,
    markscheme: str,
    answer_text: str,
    log_cache_stats: bool = True
) -> Tuple[Optional[str], dict]
```

Same return format as `get_improvement_feedback()`.

### get_batch_feedback_stats()
```python
stats = get_batch_feedback_stats(
    feedback_results: list[dict]
) -> dict
```

**Input:** List of dicts with `cache_stats` key (from the functions above)

**Returns:** Dict with:
- `total_requests`: Number of requests in batch
- `cache_hit_count`: How many requests got cache hits
- `total_cached_read_tokens`: Total tokens served from cache
- `total_cached_write_tokens`: Total tokens written to cache
- `total_uncached_tokens`: Total full-price tokens
- `total_output_tokens`: Response tokens
- `average_efficiency_pct`: Mean % from cache

## Questions?

For cache issues:
- Check logs for "Cache hit!" messages
- Run `example_student_feedback.py` to verify setup
- See troubleshooting section above

For feedback quality issues:
- Improve the `markscheme` — it's used by Claude to calibrate feedback
- Check `FEEDBACK_SYSTEM_PROMPT` in `student_feedback.py`
- Try different `AI_MODEL` (default: `claude-opus-4-8`)
