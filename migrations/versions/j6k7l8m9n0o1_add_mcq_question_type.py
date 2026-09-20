"""Add multiple-choice question type to quiz questions

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'j6k7l8m9n0o1'
down_revision = 'i5j6k7l8m9n0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('quiz_questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('question_type', sa.String(length=20), nullable=False, server_default='short_answer'))
        batch_op.add_column(sa.Column('options', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('correct_options', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('quiz_questions', schema=None) as batch_op:
        batch_op.drop_column('correct_options')
        batch_op.drop_column('options')
        batch_op.drop_column('question_type')
