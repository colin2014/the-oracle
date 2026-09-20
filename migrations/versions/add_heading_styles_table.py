"""Add heading_styles table

Revision ID: add_heading_styles
Revises: 43c41537a360
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_heading_styles'
down_revision = '43c41537a360'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('heading_styles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('heading_level', sa.String(length=3), nullable=False),
    sa.Column('font_size', sa.String(length=20), nullable=False),
    sa.Column('color', sa.String(length=7), nullable=False),
    sa.Column('font_family', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'heading_level', name='uq_user_heading_level')
    )
    op.create_index('ix_user_heading', 'heading_styles', ['user_id', 'heading_level'], unique=False)


def downgrade():
    op.drop_index('ix_user_heading', table_name='heading_styles')
    op.drop_table('heading_styles')
