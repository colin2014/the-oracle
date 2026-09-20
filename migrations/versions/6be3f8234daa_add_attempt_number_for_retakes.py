"""Add attempt_number for retakes

Revision ID: 6be3f8234daa
Revises: ee0e7217c194
Create Date: 2026-07-16 18:20:12.753893

"""
from alembic import op
import sqlalchemy as sa


revision = '6be3f8234daa'
down_revision = 'ee0e7217c194'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('quiz_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('attempt_number', sa.Integer(), nullable=True))
        batch_op.drop_constraint('uq_quiz_answer_student', type_='unique')

    op.execute('UPDATE quiz_answers SET attempt_number = 1 WHERE attempt_number IS NULL')

    with op.batch_alter_table('quiz_answers', schema=None) as batch_op:
        batch_op.alter_column('attempt_number', nullable=False)
        batch_op.create_index('ix_quiz_answer_student_question', ['student_id', 'question_id'])
        batch_op.create_unique_constraint('uq_quiz_answer_attempt', ['question_id', 'student_id', 'attempt_number'])


def downgrade():
    with op.batch_alter_table('quiz_answers', schema=None) as batch_op:
        batch_op.drop_constraint('uq_quiz_answer_attempt', type_='unique')
        batch_op.drop_index('ix_quiz_answer_student_question')
        batch_op.create_unique_constraint('uq_quiz_answer_student', ['question_id', 'student_id'])
        batch_op.drop_column('attempt_number')
