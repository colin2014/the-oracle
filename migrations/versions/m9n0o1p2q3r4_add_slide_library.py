"""Add slide_decks and topic_grade_focus (PowerPoint library)

Revision ID: m9n0o1p2q3r4
Revises: l8m9n0o1p2q3
Create Date: 2026-07-31
"""
from alembic import op
import sqlalchemy as sa


revision = 'm9n0o1p2q3r4'
down_revision = 'l8m9n0o1p2q3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'slide_decks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.String(length=60), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('embed_url', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('slide_decks', schema=None) as batch_op:
        batch_op.create_index('ix_slide_decks_topic_id', ['topic_id'])

    op.create_table(
        'topic_grade_focus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.String(length=60), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('focused', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('topic_id', 'grade', name='uq_topic_grade_focus'),
    )
    with op.batch_alter_table('topic_grade_focus', schema=None) as batch_op:
        batch_op.create_index('ix_topic_grade_focus_topic_id', ['topic_id'])


def downgrade():
    with op.batch_alter_table('topic_grade_focus', schema=None) as batch_op:
        batch_op.drop_index('ix_topic_grade_focus_topic_id')
    op.drop_table('topic_grade_focus')
    with op.batch_alter_table('slide_decks', schema=None) as batch_op:
        batch_op.drop_index('ix_slide_decks_topic_id')
    op.drop_table('slide_decks')
