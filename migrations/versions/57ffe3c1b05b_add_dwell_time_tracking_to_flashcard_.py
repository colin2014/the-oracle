"""Add dwell time tracking to flashcard progress

Revision ID: 57ffe3c1b05b
Revises: h4i5j6k7l8m9
Create Date: 2026-07-15 09:03:36.254338

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57ffe3c1b05b'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('flashcard_progress', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_dwell_seconds', sa.Float(), nullable=False, server_default='0.0'))


def downgrade():
    with op.batch_alter_table('flashcard_progress', schema=None) as batch_op:
        batch_op.drop_column('total_dwell_seconds')
