"""Add quiz_questions and quiz_answers tables

Revision ID: d9e0f1a2b3c4
Revises: add_heading_styles
Create Date: 2026-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9e0f1a2b3c4'
down_revision = 'add_heading_styles'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('quiz_questions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('book_folder', sa.String(length=120), nullable=False),
    sa.Column('page_id', sa.String(length=50), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('markscheme', sa.Text(), nullable=False),
    sa.Column('keywords', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_quiz_question_page', 'quiz_questions', ['book_folder', 'page_id'], unique=False)

    op.create_table('quiz_answers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('question_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('answer_text', sa.Text(), nullable=False),
    sa.Column('auto_correct', sa.Boolean(), nullable=True),
    sa.Column('auto_method', sa.String(length=20), nullable=False),
    sa.Column('auto_note', sa.Text(), nullable=True),
    sa.Column('final_correct', sa.Boolean(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('submitted_at', sa.DateTime(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['question_id'], ['quiz_questions.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('question_id', 'student_id', name='uq_quiz_answer_student')
    )
    op.create_index(op.f('ix_quiz_answers_question_id'), 'quiz_answers', ['question_id'], unique=False)
    op.create_index(op.f('ix_quiz_answers_student_id'), 'quiz_answers', ['student_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_quiz_answers_student_id'), table_name='quiz_answers')
    op.drop_index(op.f('ix_quiz_answers_question_id'), table_name='quiz_answers')
    op.drop_table('quiz_answers')
    op.drop_index('ix_quiz_question_page', table_name='quiz_questions')
    op.drop_table('quiz_questions')
