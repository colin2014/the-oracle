#!/usr/bin/env python3
"""Example demonstrating student feedback generation with prompt caching.

Run this to see how the caching reduces token usage:
- First request: writes cache (1.25× cost for system prompt)
- Second+ requests: read from cache (0.1× cost for system prompt)
- Expected savings: ~90% on system prompt tokens for 2+ requests
"""

import os
from student_feedback import (
    get_improvement_feedback,
    get_correction_feedback,
    get_batch_feedback_stats,
)

# Sample quiz data (from your app)
QUESTIONS = [
    {
        "id": 1,
        "question": "What is photosynthesis?",
        "markscheme": "Photosynthesis is the process where plants use sunlight, water, and CO2 to produce glucose and oxygen. Must mention: sunlight/light energy, water, CO2, glucose/sugar, oxygen.",
        "correct_answers": [
            "Plants make food using light, water, and CO2.",
            "It's when plants turn light into chemical energy.",
        ],
        "incorrect_answers": [
            "Plants use sunlight to grow.",
            "It's the process where plants breathe.",
        ],
    },
    {
        "id": 2,
        "question": "What is the role of mitochondria?",
        "markscheme": "Mitochondria are the powerhouse of the cell. They produce ATP (energy) through cellular respiration. Must mention: energy production, ATP, or cellular respiration.",
        "correct_answers": [
            "Mitochondria produce energy for the cell.",
            "They break down glucose to make ATP.",
        ],
        "incorrect_answers": [
            "Mitochondria control the cell.",
            "They store DNA.",
        ],
    },
    {
        "id": 3,
        "question": "How does DNA store genetic information?",
        "markscheme": "DNA stores information in the sequence of nucleotide bases (A, T, G, C). This sequence is read to produce proteins. Must mention: bases/nucleotides, sequence, or protein synthesis.",
        "correct_answers": [
            "The order of bases in DNA stores genetic information.",
            "DNA uses base sequences to code for proteins.",
        ],
        "incorrect_answers": [
            "DNA stores information in its shape.",
            "The color of DNA determines the information.",
        ],
    },
]


def demo_improvement_feedback():
    """Show improvement feedback for correct answers (with cache hits)."""
    print("=" * 60)
    print("IMPROVEMENT FEEDBACK DEMO (Correct Answers)")
    print("=" * 60)
    print()

    feedback_results = []

    for q in QUESTIONS:
        for i, answer in enumerate(q["correct_answers"], 1):
            print(f"Question: {q['question']}")
            print(f"Student Answer: {answer}")
            print("-" * 40)

            feedback, cache_stats = get_improvement_feedback(
                question_text=q["question"],
                markscheme=q["markscheme"],
                answer_text=answer,
                log_cache_stats=True,
            )

            if feedback:
                print(f"--- Feedback:\n{feedback}\n")
            else:
                print("(No feedback generated)\n")

            feedback_results.append({
                "question_id": q["id"],
                "answer_num": i,
                "cache_stats": cache_stats,
            })

            print()

    # Show batch stats
    print("=" * 60)
    print("BATCH STATISTICS (All Improvement Feedback)")
    print("=" * 60)
    stats = get_batch_feedback_stats(feedback_results)
    print(f"Total requests: {stats['total_requests']}")
    print(f"Cache hits: {stats['cache_hit_count']}")
    print(f"Tokens from cache: {stats['total_cached_read_tokens']}")
    print(f"Tokens written to cache: {stats['total_cached_write_tokens']}")
    print(f"Uncached input tokens: {stats['total_uncached_tokens']}")
    print(f"Average efficiency: {stats['average_efficiency_pct']:.1f}% from cache")
    print(f"Total input tokens: {stats['total_input_tokens']}")
    print(f"Total output tokens: {stats['total_output_tokens']}")
    print()


def demo_correction_feedback():
    """Show correction feedback for incorrect answers (with cache hits)."""
    print("=" * 60)
    print("CORRECTION FEEDBACK DEMO (Incorrect Answers)")
    print("=" * 60)
    print()

    feedback_results = []

    for q in QUESTIONS:
        for i, answer in enumerate(q["incorrect_answers"], 1):
            print(f"Question: {q['question']}")
            print(f"Student Answer: {answer}")
            print("-" * 40)

            feedback, cache_stats = get_correction_feedback(
                question_text=q["question"],
                markscheme=q["markscheme"],
                answer_text=answer,
                log_cache_stats=True,
            )

            if feedback:
                print(f"--- Feedback:\n{feedback}\n")
            else:
                print("(No feedback generated)\n")

            feedback_results.append({
                "question_id": q["id"],
                "answer_num": i,
                "cache_stats": cache_stats,
            })

            print()

    # Show batch stats
    print("=" * 60)
    print("📊 BATCH STATISTICS (All Correction Feedback)")
    print("=" * 60)
    stats = get_batch_feedback_stats(feedback_results)
    print(f"Total requests: {stats['total_requests']}")
    print(f"Cache hits: {stats['cache_hit_count']}")
    print(f"Tokens from cache: {stats['total_cached_read_tokens']}")
    print(f"Tokens written to cache: {stats['total_cached_write_tokens']}")
    print(f"Uncached input tokens: {stats['total_uncached_tokens']}")
    print(f"Average efficiency: {stats['average_efficiency_pct']:.1f}% from cache")
    print(f"Total input tokens: {stats['total_input_tokens']}")
    print(f"Total output tokens: {stats['total_output_tokens']}")
    print()
    print("[Tip] The cache is 5 minutes long. Run again within 5 min to see")
    print("   even more cache hits! Second request onwards: 90% savings on")
    print("   system prompt tokens.")
    print()


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[Error] ANTHROPIC_API_KEY not set")
        print("   Set it in .env or export it:")
        print("   export ANTHROPIC_API_KEY='sk-ant-...'")
        exit(1)

    print("\n>>> Student Feedback with Prompt Caching Demo\n")

    try:
        demo_improvement_feedback()
        demo_correction_feedback()

        print("=" * 60)
        print("[OK] Demo Complete!")
        print("=" * 60)
        print("\nKey Insights:")
        print("• First request: System prompt written to cache (1.25× cost)")
        print("• Subsequent requests: Read system prompt from cache (0.1× cost)")
        print("• Savings after 2 requests: ~11% on input tokens")
        print("• Savings after 5+ requests: ~18% on input tokens")
        print("• Cache duration: 5 minutes (ephemeral)")
        print()

    except KeyboardInterrupt:
        print("\n[Interrupted] Demo interrupted")
    except Exception as e:
        print(f"[Error] Error: {e}")
        raise
