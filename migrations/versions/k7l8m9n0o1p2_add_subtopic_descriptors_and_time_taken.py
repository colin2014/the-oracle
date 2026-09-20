"""Add subtopic_descriptors table and test_submissions.time_taken_seconds

Revision ID: k7l8m9n0o1p2
Revises: cf15fe50887c
Create Date: 2026-07-31

The descriptor table is populated from the "Subtopic Descriptors" sheet on the
next question-bank import; it starts empty and the reports degrade to subtopic
titles alone until then.

time_taken_seconds is backfilled from the existing timestamps so historical
submissions keep reporting a duration, clamped to the paper's time limit for
rows whose auto-submit landed late.
"""
from alembic import op
import sqlalchemy as sa


revision = 'k7l8m9n0o1p2'
down_revision = 'cf15fe50887c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'subtopic_descriptors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('descriptor', sa.Text(), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=True),
        sa.Column('total_marks', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )

    with op.batch_alter_table('test_submissions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('time_taken_seconds', sa.Integer(), nullable=True))

    # Backfill. SQLite has no date-diff that works on these stored strings, so use
    # julianday(); the clamp mirrors _finalize_submission.
    op.execute("""
        UPDATE test_submissions
           SET time_taken_seconds = MIN(
                   CAST((julianday(submitted_at) - julianday(started_at)) * 86400 AS INTEGER),
                   time_limit_minutes * 60
               )
         WHERE submitted_at IS NOT NULL
           AND started_at IS NOT NULL
           AND CAST((julianday(submitted_at) - julianday(started_at)) * 86400 AS INTEGER) >= 0
    """)


def downgrade():
    with op.batch_alter_table('test_submissions', schema=None) as batch_op:
        batch_op.drop_column('time_taken_seconds')
    op.drop_table('subtopic_descriptors')
