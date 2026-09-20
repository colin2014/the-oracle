"""Add book_vocabulary table for managing editable vocabulary

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2026-07-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g3h4i5j6k7l8'
down_revision = 'f2g3h4i5j6k7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('book_vocabulary',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('book_folder', sa.String(length=120), nullable=False),
    sa.Column('page_id', sa.String(length=50), nullable=True),
    sa.Column('term', sa.Text(), nullable=False),
    sa.Column('definition', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vocab_book'), 'book_vocabulary', ['book_folder'], unique=False)
    op.create_index(op.f('ix_vocab_book_page'), 'book_vocabulary', ['book_folder', 'page_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_vocab_book_page'), table_name='book_vocabulary')
    op.drop_index(op.f('ix_vocab_book'), table_name='book_vocabulary')
    op.drop_table('book_vocabulary')
