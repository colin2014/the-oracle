"""Cache the AI-written test report narrative on the submission

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-08-06

The report's "What you did well" and "Where to go next" prose is written by a
model. Rendering the report and exporting its PDF are two separate requests over
the same submission, so without a cache every student pays for the call twice.
The key column stores a fingerprint of the marks the prose was written from — a
teacher adjusting an answer changes the fingerprint and the narrative is
rewritten on the next view.
"""
from alembic import op
import sqlalchemy as sa


revision = 'q2r3s4t5u6v7'
down_revision = 'p1q2r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('test_submissions') as batch_op:
        batch_op.add_column(sa.Column('report_narrative', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('report_narrative_key', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('test_submissions') as batch_op:
        batch_op.drop_column('report_narrative_key')
        batch_op.drop_column('report_narrative')
