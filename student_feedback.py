"""Student feedback generation with prompt caching.

Caches the stable system prompt to reduce token usage across multiple student answers.
First request: pays 1.25× for system prompt write
Subsequent requests: pay 0.1× for system prompt read (90% savings)
Break-even: 2 requests with 5-minute ephemeral cache
"""

import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Stable system prompt that will be cached
FEEDBACK_SYSTEM_PROMPT = (
    "You give students feedback on short-answer quiz responses that already "
    "earned the mark. In 2-3 sentences, speaking directly to the student, say "
    "what would make the answer even stronger — a missing nuance, more precise "
    "terminology, or an idea from the markscheme they touched only lightly. "
    "Wrap each specific improvement in **double asterisks** so it renders bold. "
    "Be encouraging and concrete; no headings or lists, just the sentences."
)

CORRECTION_FEEDBACK_PROMPT = (
    "You help students understand why their answer was incorrect. "
    "Be supportive and educational. In 2-3 sentences, explain what they missed "
    "and what would make it correct. Wrap specific concepts in **double asterisks**. "
    "Encourage them to try again after understanding the feedback."
)


def get_improvement_feedback(
    question_text: str,
    markscheme: str,
    answer_text: str,
    log_cache_stats: bool = True
) -> Tuple[Optional[str], dict]:
    """Generate improvement feedback for a correct answer using cached system prompt.

    Args:
        question_text: The quiz question
        markscheme: Teacher's marking guide
        answer_text: Student's answer that already earned the mark
        log_cache_stats: Whether to log cache statistics

    Returns:
        Tuple of (feedback_text, cache_stats) where cache_stats includes:
        - cache_creation_tokens: tokens written to cache
        - cache_read_tokens: tokens served from cache
        - efficiency_pct: percentage of tokens from cache
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, {}

    try:
        import anthropic
        client = anthropic.Anthropic()

        response = client.messages.create(
            model=os.environ.get("AI_MODEL", "claude-opus-4-8"),
            max_tokens=1024,
            # Top-level auto-caching: caches the last cacheable block
            cache_control={"type": "ephemeral"},
            system=[
                {
                    "type": "text",
                    "text": FEEDBACK_SYSTEM_PROMPT,
                    # Cache the stable feedback instructions
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[{
                "role": "user",
                "content": (
                    f"QUESTION: {question_text}\n\n"
                    f"MARKSCHEME: {markscheme}\n\n"
                    f"STUDENT ANSWER (marked correct): {answer_text}"
                ),
            }],
        )

        # Extract feedback text
        text = next((b.text for b in response.content if b.type == "text"), "").strip()
        feedback = text[:2000] or None

        # Compute cache statistics
        cache_stats = {
            "cache_creation_tokens": response.usage.cache_creation_input_tokens,
            "cache_read_tokens": response.usage.cache_read_input_tokens,
            "uncached_input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        # Calculate efficiency percentage
        total_cached = (
            cache_stats["cache_creation_tokens"] +
            cache_stats["cache_read_tokens"]
        )
        if total_cached > 0:
            cache_stats["efficiency_pct"] = round(
                (cache_stats["cache_read_tokens"] / total_cached) * 100, 1
            )
        else:
            cache_stats["efficiency_pct"] = 0.0

        if log_cache_stats and cache_stats["cache_read_tokens"] > 0:
            logger.info(
                f"Cache hit! Saved {cache_stats['cache_read_tokens']} tokens "
                f"({cache_stats['efficiency_pct']:.0f}% from cache)"
            )
        elif log_cache_stats and cache_stats["cache_creation_tokens"] > 0:
            logger.info(
                f"Cache written: {cache_stats['cache_creation_tokens']} tokens "
                f"(5-min ephemeral cache)"
            )

        return feedback, cache_stats

    except Exception as e:
        logger.exception("Error generating improvement feedback")
        return None, {}


def get_correction_feedback(
    question_text: str,
    markscheme: str,
    answer_text: str,
    log_cache_stats: bool = True
) -> Tuple[Optional[str], dict]:
    """Generate correction feedback for an incorrect answer using cached system prompt.

    Args:
        question_text: The quiz question
        markscheme: Teacher's marking guide
        answer_text: Student's incorrect answer
        log_cache_stats: Whether to log cache statistics

    Returns:
        Tuple of (feedback_text, cache_stats)
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, {}

    try:
        import anthropic
        client = anthropic.Anthropic()

        response = client.messages.create(
            model=os.environ.get("AI_MODEL", "claude-opus-4-8"),
            max_tokens=1024,
            cache_control={"type": "ephemeral"},
            system=[
                {
                    "type": "text",
                    "text": CORRECTION_FEEDBACK_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[{
                "role": "user",
                "content": (
                    f"QUESTION: {question_text}\n\n"
                    f"MARKSCHEME (what would be correct): {markscheme}\n\n"
                    f"STUDENT ANSWER (which was incorrect): {answer_text}"
                ),
            }],
        )

        text = next((b.text for b in response.content if b.type == "text"), "").strip()
        feedback = text[:2000] or None

        cache_stats = {
            "cache_creation_tokens": response.usage.cache_creation_input_tokens,
            "cache_read_tokens": response.usage.cache_read_input_tokens,
            "uncached_input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        total_cached = (
            cache_stats["cache_creation_tokens"] +
            cache_stats["cache_read_tokens"]
        )
        if total_cached > 0:
            cache_stats["efficiency_pct"] = round(
                (cache_stats["cache_read_tokens"] / total_cached) * 100, 1
            )
        else:
            cache_stats["efficiency_pct"] = 0.0

        if log_cache_stats and cache_stats["cache_read_tokens"] > 0:
            logger.info(
                f"Cache hit! Saved {cache_stats['cache_read_tokens']} tokens "
                f"({cache_stats['efficiency_pct']:.0f}% from cache)"
            )
        elif log_cache_stats and cache_stats["cache_creation_tokens"] > 0:
            logger.info(
                f"Cache written: {cache_stats['cache_creation_tokens']} tokens"
            )

        return feedback, cache_stats

    except Exception as e:
        logger.exception("Error generating correction feedback")
        return None, {}


def get_batch_feedback_stats(feedback_results: list[dict]) -> dict:
    """Aggregate cache statistics from a batch of feedback generations.

    Args:
        feedback_results: List of dicts with 'cache_stats' key from get_*_feedback calls

    Returns:
        Aggregated statistics showing total tokens cached vs. uncached
    """
    total_cached_read = sum(
        r.get("cache_stats", {}).get("cache_read_tokens", 0)
        for r in feedback_results
    )
    total_cached_write = sum(
        r.get("cache_stats", {}).get("cache_creation_tokens", 0)
        for r in feedback_results
    )
    total_uncached = sum(
        r.get("cache_stats", {}).get("uncached_input_tokens", 0)
        for r in feedback_results
    )
    total_output = sum(
        r.get("cache_stats", {}).get("output_tokens", 0)
        for r in feedback_results
    )

    total_input = total_uncached + total_cached_read + total_cached_write

    return {
        "total_requests": len(feedback_results),
        "total_cached_read_tokens": total_cached_read,
        "total_cached_write_tokens": total_cached_write,
        "total_uncached_tokens": total_uncached,
        "total_output_tokens": total_output,
        "total_input_tokens": total_input,
        "cache_hit_count": sum(
            1 for r in feedback_results
            if r.get("cache_stats", {}).get("cache_read_tokens", 0) > 0
        ),
        "average_efficiency_pct": round(
            sum(r.get("cache_stats", {}).get("efficiency_pct", 0)
                for r in feedback_results) / max(1, len(feedback_results)),
            1
        ),
    }
