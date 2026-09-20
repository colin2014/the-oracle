"""Keep the workbook's own question key separate from the displayed number

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-08-06

Deleting a question from a subtopic now renumbers the ones after it, so the
subtopic reads Q01..Qnn with no gaps. That makes `qid` a *display* label which
moves — and it was also the key questions.xlsx is joined on at import, so after
a renumber a re-import would have written workbook Q05's content over the row
now called Q05 (which used to be Q06), silently corrupting the bank.

`source_qid` holds the immutable workbook key. Import matches on it; renumbering
only ever touches `qid`. Existing rows are backfilled from their current qid,
which is correct because nothing has been renumbered before this migration.
"""
from alembic import op
import sqlalchemy as sa


revision = 'r3s4t5u6v7w8'
down_revision = 'q2r3s4t5u6v7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('test_questions') as batch_op:
        batch_op.add_column(sa.Column('source_qid', sa.String(length=40), nullable=True))
    op.execute("UPDATE test_questions SET source_qid = qid WHERE source_qid IS NULL")
    op.create_index('ix_test_question_source_qid', 'test_questions', ['source_qid'])


def downgrade():
    op.drop_index('ix_test_question_source_qid', table_name='test_questions')
    with op.batch_alter_table('test_questions') as batch_op:
        batch_op.drop_column('source_qid')
