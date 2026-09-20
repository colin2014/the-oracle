"""Add student_report_cache

Revision ID: l8m9n0o1p2q3
Revises: k7l8m9n0o1p2
Create Date: 2026-07-31

Caches the AI-generated report card per student so the on-screen view and the
PDF export share one generation instead of making an Anthropic call each.
Starts empty; the first view of each student repopulates it.
"""
from alembic import op
import sqlalchemy as sa


revision = 'l8m9n0o1p2q3'
down_revision = 'k7l8m9n0o1p2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'student_report_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('prompt_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('report_json', sa.Text(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id'),
    )
    with op.batch_alter_table('student_report_cache', schema=None) as batch_op:
        batch_op.create_index('ix_student_report_cache_student_id', ['student_id'])


def downgrade():
    with op.batch_alter_table('student_report_cache', schema=None) as batch_op:
        batch_op.drop_index('ix_student_report_cache_student_id')
    op.drop_table('student_report_cache')
