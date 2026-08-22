#!/usr/bin/env python
"""Delete all test data, assignments, activity, and quiz data."""

from app import app, db
from models import (
    ReadingAssignment,
    ReadingActivity,
    ReadingDailyLog,
    StudentConfidence,
)

# Import quiz/flashcard models if they exist
try:
    from models import (
        Quiz, QuizQuestion, QuizAttempt, QuizAttemptAnswer,
        FlashcardSet, Flashcard, FlashcardProgress, FlashcardStudySession,
        BookVocabulary, VocabularyProgress
    )
    QUIZ_MODELS_EXIST = True
except ImportError:
    QUIZ_MODELS_EXIST = False

# Import other tracking models if they exist
try:
    from models import ReadingTimer, StudentFeedback, ImprovementAnalysisCache
    OTHER_MODELS_EXIST = True
except ImportError:
    OTHER_MODELS_EXIST = False

def cleanup_test_data():
    with app.app_context():
        print("Starting cleanup of test data...\n")

        # Delete reading assignments
        count = ReadingAssignment.query.delete()
        print(f"[OK] Deleted {count} reading assignments")

        # Delete reading activity
        count = ReadingActivity.query.delete()
        print(f"[OK] Deleted {count} reading activity records")

        # Delete reading daily logs
        count = ReadingDailyLog.query.delete()
        print(f"[OK] Deleted {count} reading daily log records")

        # Delete student confidence ratings
        count = StudentConfidence.query.delete()
        print(f"[OK] Deleted {count} student confidence records")

        # Delete quiz data if models exist
        if QUIZ_MODELS_EXIST:
            try:
                count = QuizAttemptAnswer.query.delete()
                print(f"[OK] Deleted {count} quiz attempt answers")

                count = QuizAttempt.query.delete()
                print(f"[OK] Deleted {count} quiz attempts")

                count = QuizQuestion.query.delete()
                print(f"[OK] Deleted {count} quiz questions")

                count = Quiz.query.delete()
                print(f"[OK] Deleted {count} quizzes")
            except Exception as e:
                print(f"[WARN] Could not delete quiz data: {e}")

        # Delete flashcard data if models exist
        if QUIZ_MODELS_EXIST:
            try:
                count = FlashcardStudySession.query.delete()
                print(f"[OK] Deleted {count} flashcard study sessions")

                count = FlashcardProgress.query.delete()
                print(f"[OK] Deleted {count} flashcard progress records")

                count = Flashcard.query.delete()
                print(f"[OK] Deleted {count} flashcards")

                count = FlashcardSet.query.delete()
                print(f"[OK] Deleted {count} flashcard sets")

                count = VocabularyProgress.query.delete()
                print(f"[OK] Deleted {count} vocabulary progress records")

                count = BookVocabulary.query.delete()
                print(f"[OK] Deleted {count} book vocabulary entries")
            except Exception as e:
                print(f"[WARN] Could not delete flashcard data: {e}")

        # Delete other tracking data if models exist
        if OTHER_MODELS_EXIST:
            try:
                count = StudentFeedback.query.delete()
                print(f"[OK] Deleted {count} student feedback records")

                count = ImprovementAnalysisCache.query.delete()
                print(f"[OK] Deleted {count} improvement analysis cache records")
            except Exception as e:
                print(f"[WARN] Could not delete other data: {e}")

        db.session.commit()
        print("\n[OK] Test data cleanup complete!")
        print("\nPreserved:")
        print("- Admin and Test user accounts")
        print("- Class of 27 (3 HL students)")
        print("- Class of 28 (6 HL + 2 SL students)")

if __name__ == "__main__":
    cleanup_test_data()
