"""Add question marks, summaries, and answer insights for weighted grading

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8c9d0e1f2a3'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('quiz_questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('summary', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('marks', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('difficulty', sa.String(length=20), nullable=True, server_default='medium'))

    with op.batch_alter_table('quiz_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('marks_awarded', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('what_you_know', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('improving_understanding', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('quiz_answers', schema=None) as batch_op:
        batch_op.drop_column('improving_understanding')
        batch_op.drop_column('what_you_know')
        batch_op.drop_column('marks_awarded')

    with op.batch_alter_table('quiz_questions', schema=None) as batch_op:
        batch_op.drop_column('difficulty')
        batch_op.drop_column('marks')
        batch_op.drop_column('summary')
