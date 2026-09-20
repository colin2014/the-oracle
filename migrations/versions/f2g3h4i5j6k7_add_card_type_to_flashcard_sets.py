"""Add card_type field to flashcard_sets table

Revision ID: f2g3h4i5j6k7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-14 20:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2g3h4i5j6k7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('flashcard_sets',
        sa.Column('card_type', sa.String(length=20), nullable=False, server_default='flashcard')
    )


def downgrade():
    op.drop_column('flashcard_sets', 'card_type')
