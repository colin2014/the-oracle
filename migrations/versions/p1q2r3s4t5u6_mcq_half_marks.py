"""MCQ questions are worth 0.5 marks

Revision ID: p1q2r3s4t5u6
Revises: 07636ae09ec7
Create Date: 2026-08-06

At 1 mark each, MCQs dominated a paper's total and skewed how a student's
performance read. They're fixed at half a mark now, which means every mark
column in the test-builder tables has to hold halves — Integer -> Float — and
existing MCQ rows (plus the marks already awarded for them) are rescaled.

Written questions are untouched: they keep whole marks.
"""
from alembic import op
import sqlalchemy as sa


revision = 'p1q2r3s4t5u6'
down_revision = '07636ae09ec7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('test_questions') as batch_op:
        batch_op.alter_column('marks', existing_type=sa.Integer(), type_=sa.Float(),
                              existing_nullable=False)
    with op.batch_alter_table('test_answers') as batch_op:
        batch_op.alter_column('marks_awarded', existing_type=sa.Integer(), type_=sa.Float(),
                              existing_nullable=True)
    with op.batch_alter_table('test_submissions') as batch_op:
        batch_op.alter_column('total_marks_awarded', existing_type=sa.Integer(), type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('total_marks_possible', existing_type=sa.Integer(), type_=sa.Float(),
                              existing_nullable=True)

    # Existing data. Order matters: awarded marks are halved off the *old* question
    # value, so the answers are rescaled before the questions are.
    op.execute("""
        UPDATE test_answers SET marks_awarded = marks_awarded / 2.0
        WHERE marks_awarded IS NOT NULL
          AND question_id IN (SELECT id FROM test_questions WHERE question_type = 'mcq')
    """)
    op.execute("UPDATE test_questions SET marks = 0.5 WHERE question_type = 'mcq'")

    # Submission totals are derived, so recompute rather than scale — the stored
    # possible total also has to match the paper's new sum.
    op.execute("""
        UPDATE test_submissions SET total_marks_awarded = (
            SELECT SUM(COALESCE(a.marks_awarded, 0)) FROM test_answers a
            WHERE a.submission_id = test_submissions.id
        ) WHERE total_marks_awarded IS NOT NULL
    """)
    op.execute("""
        UPDATE test_submissions SET total_marks_possible = (
            SELECT SUM(q.marks) FROM test_paper_questions pq
            JOIN test_questions q ON q.id = pq.question_id
            WHERE pq.test_paper_id = test_submissions.test_paper_id
        ) WHERE total_marks_possible IS NOT NULL
    """)


def downgrade():
    # Put MCQs back to a whole mark and re-derive, then narrow the columns.
    op.execute("""
        UPDATE test_answers SET marks_awarded = marks_awarded * 2.0
        WHERE marks_awarded IS NOT NULL
          AND question_id IN (SELECT id FROM test_questions WHERE question_type = 'mcq')
    """)
    op.execute("UPDATE test_questions SET marks = 1 WHERE question_type = 'mcq'")
    op.execute("""
        UPDATE test_submissions SET total_marks_awarded = (
            SELECT SUM(COALESCE(a.marks_awarded, 0)) FROM test_answers a
            WHERE a.submission_id = test_submissions.id
        ) WHERE total_marks_awarded IS NOT NULL
    """)
    op.execute("""
        UPDATE test_submissions SET total_marks_possible = (
            SELECT SUM(q.marks) FROM test_paper_questions pq
            JOIN test_questions q ON q.id = pq.question_id
            WHERE pq.test_paper_id = test_submissions.test_paper_id
        ) WHERE total_marks_possible IS NOT NULL
    """)

    with op.batch_alter_table('test_submissions') as batch_op:
        batch_op.alter_column('total_marks_possible', existing_type=sa.Float(), type_=sa.Integer(),
                              existing_nullable=True)
        batch_op.alter_column('total_marks_awarded', existing_type=sa.Float(), type_=sa.Integer(),
                              existing_nullable=True)
    with op.batch_alter_table('test_answers') as batch_op:
        batch_op.alter_column('marks_awarded', existing_type=sa.Float(), type_=sa.Integer(),
                              existing_nullable=True)
    with op.batch_alter_table('test_questions') as batch_op:
        batch_op.alter_column('marks', existing_type=sa.Float(), type_=sa.Integer(),
                              existing_nullable=False)
