"""Add page_summaries table for AI page overviews

Revision ID: a7b8c9d0e1f2
Revises: 6be3f8234daa
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = '6be3f8234daa'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('page_summaries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('book_folder', sa.String(length=120), nullable=False),
    sa.Column('page_id', sa.String(length=50), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('generated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('book_folder', 'page_id', name='uq_page_summary_page')
    )


def downgrade():
    op.drop_table('page_summaries')
