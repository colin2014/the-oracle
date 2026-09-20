"""Add improvement_analysis cache column to quiz_answers

Revision ID: i5j6k7l8m9n0
Revises: b8c9d0e1f2a3
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i5j6k7l8m9n0'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('quiz_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('improvement_analysis', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('quiz_answers', schema=None) as batch_op:
        batch_op.drop_column('improvement_analysis')
