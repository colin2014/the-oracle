"""Add HL/SL level tracking to class enrollments

Adds a ``level`` column to ``class_enrollments`` to track whether a student
is taking the course at Higher Level (HL) or Standard Level (SL).

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa


revision = 'c8d9e0f1a2b3'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('class_enrollments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('level', sa.String(2), nullable=True))


def downgrade():
    with op.batch_alter_table('class_enrollments', schema=None) as batch_op:
        batch_op.drop_column('level')
