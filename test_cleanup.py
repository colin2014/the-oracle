"""Cleanup task for expired test submissions."""

from datetime import datetime, timedelta
from extensions import db
from models import TestSubmission


def cleanup_expired_tests(hours=3):
    """
    Clean up expired test submissions.

    - Live tests (in_progress) older than N hours: auto-submit them
    - Unstarted tests with no answers older than N hours: delete them

    Args:
        hours: Number of hours to consider "expired" (default: 3)

    Returns:
        dict with counts of cleaned up tests
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    # Find all in_progress submissions older than the cutoff
    expired_live = TestSubmission.query.filter(
        TestSubmission.status == "in_progress",
        TestSubmission.started_at < cutoff_time
    ).all()

    auto_submitted = 0
    for submission in expired_live:
        # Auto-submit the test
        submission.status = "submitted"
        submission.submitted_at = datetime.utcnow()
        # Calculate time taken
        if submission.time_taken_seconds is None:
            submission.time_taken_seconds = int(
                (submission.submitted_at - submission.started_at).total_seconds()
            )
        auto_submitted += 1

    # Find unstarted submissions with no answers older than the cutoff
    # (These are tests that were created but never actually started)
    deleted_unstarted = 0
    all_old_in_progress = TestSubmission.query.filter(
        TestSubmission.status == "in_progress",
        TestSubmission.started_at < cutoff_time
    ).all()

    for submission in all_old_in_progress:
        # Check if this submission has any answers
        if not submission.answers:
            # No answers recorded - safe to delete
            db.session.delete(submission)
            deleted_unstarted += 1

    # Commit all changes
    db.session.commit()

    return {
        "auto_submitted": auto_submitted,
        "deleted_unstarted": deleted_unstarted,
        "total_cleaned": auto_submitted + deleted_unstarted,
        "cutoff_time": cutoff_time.isoformat()
    }


if __name__ == "__main__":
    from app import app
    with app.app_context():
        result = cleanup_expired_tests(hours=3)
        print(f"Cleanup Results:")
        print(f"  Auto-submitted (saved): {result['auto_submitted']}")
        print(f"  Deleted (unstarted): {result['deleted_unstarted']}")
        print(f"  Total cleaned: {result['total_cleaned']}")
        print(f"  Cutoff time: {result['cutoff_time']}")
