"""Add flashcard_study_sessions table for per-attempt analytics

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-07-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h4i5j6k7l8m9'
down_revision = 'g3h4i5j6k7l8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'flashcard_study_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('set_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False, server_default='flashcard'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0'),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('cards_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cards_correct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cards_incorrect', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['set_id'], ['flashcard_sets.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_flashcard_study_sessions_set_id', 'flashcard_study_sessions', ['set_id'])
    op.create_index('ix_flashcard_study_sessions_student_id', 'flashcard_study_sessions', ['student_id'])
    op.create_index('ix_fss_set_student', 'flashcard_study_sessions', ['set_id', 'student_id'])


def downgrade():
    op.drop_index('ix_fss_set_student', table_name='flashcard_study_sessions')
    op.drop_index('ix_flashcard_study_sessions_student_id', table_name='flashcard_study_sessions')
    op.drop_index('ix_flashcard_study_sessions_set_id', table_name='flashcard_study_sessions')
    op.drop_table('flashcard_study_sessions')
