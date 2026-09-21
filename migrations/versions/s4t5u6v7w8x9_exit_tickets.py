"""Exit tickets: web quizzes per syllabus subtopic

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-09-21

Five new tables (nothing existing is altered):
  exit_tickets, exit_ticket_questions, exit_ticket_assignments,
  exit_ticket_submissions, exit_ticket_answers
"""
from alembic import op
import sqlalchemy as sa


revision = 's4t5u6v7w8x9'
down_revision = 'r3s4t5u6v7w8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'exit_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=True),
        sa.Column('topic_id', sa.String(length=60), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('objective', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('allow_retries', sa.Boolean(), nullable=False),
        sa.Column('show_answers', sa.String(length=10), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_exit_tickets_code', 'exit_tickets', ['code'])
    op.create_index('ix_exit_tickets_topic_id', 'exit_tickets', ['topic_id'])

    op.create_table(
        'exit_ticket_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('qtype', sa.String(length=20), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('marks', sa.Float(), nullable=False),
        sa.Column('data', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['exit_tickets.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_exit_ticket_questions_ticket_id', 'exit_ticket_questions', ['ticket_id'])

    op.create_table(
        'exit_ticket_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.Column('student_id', sa.Integer(), nullable=True),
        sa.Column('assigned_by_id', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['exit_tickets.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_exit_ticket_assignments_ticket_id', 'exit_ticket_assignments', ['ticket_id'])
    op.create_index('ix_exit_ticket_assignments_class_id', 'exit_ticket_assignments', ['class_id'])
    op.create_index('ix_exit_ticket_assignments_student_id', 'exit_ticket_assignments', ['student_id'])

    op.create_table(
        'exit_ticket_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=True),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('total_awarded', sa.Float(), nullable=True),
        sa.Column('total_possible', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=True),
        sa.Column('reflection_note', sa.Text(), nullable=True),
        sa.Column('layout', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['assignment_id'], ['exit_ticket_assignments.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['exit_tickets.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_id', 'student_id', 'attempt_number', name='uq_exit_ticket_attempt'),
    )
    op.create_index('ix_exit_ticket_submissions_ticket_id', 'exit_ticket_submissions', ['ticket_id'])
    op.create_index('ix_exit_ticket_submissions_assignment_id', 'exit_ticket_submissions', ['assignment_id'])
    op.create_index('ix_exit_ticket_submissions_student_id', 'exit_ticket_submissions', ['student_id'])

    op.create_table(
        'exit_ticket_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('marks_awarded', sa.Float(), nullable=True),
        sa.Column('marks_possible', sa.Float(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('marked_by', sa.String(length=10), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('ai_tries', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['exit_ticket_questions.id']),
        sa.ForeignKeyConstraint(['submission_id'], ['exit_ticket_submissions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id', 'question_id', name='uq_exit_ticket_answer_question'),
    )
    op.create_index('ix_exit_ticket_answers_submission_id', 'exit_ticket_answers', ['submission_id'])
    op.create_index('ix_exit_ticket_answers_question_id', 'exit_ticket_answers', ['question_id'])


def downgrade():
    op.drop_table('exit_ticket_answers')
    op.drop_table('exit_ticket_submissions')
    op.drop_table('exit_ticket_assignments')
    op.drop_table('exit_ticket_questions')
    op.drop_table('exit_tickets')
