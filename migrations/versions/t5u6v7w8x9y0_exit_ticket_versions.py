"""Exit tickets: keep history when a ticket is edited

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-09-21

* exit_tickets.version            bumped when a save changes the questions
* exit_ticket_questions.active    removed questions are hidden, not deleted (attempts keep their history)
* exit_ticket_submissions.snapshot / ticket_version
                                  the questions exactly as they were when the attempt started

Attempts that already exist are given a snapshot of their ticket's current questions, which is what they
were taken on (nothing could be edited without changing them before this migration).
"""
import json

from alembic import op
import sqlalchemy as sa


revision = 't5u6v7w8x9y0'
down_revision = 's4t5u6v7w8x9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('exit_tickets') as batch:
        batch.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    with op.batch_alter_table('exit_ticket_questions') as batch:
        batch.add_column(sa.Column('active', sa.Boolean(), nullable=False, server_default='1'))
    with op.batch_alter_table('exit_ticket_submissions') as batch:
        batch.add_column(sa.Column('snapshot', sa.Text(), nullable=True))
        batch.add_column(sa.Column('ticket_version', sa.Integer(), nullable=True))

    conn = op.get_bind()
    for sid, tid in conn.execute(sa.text("SELECT id, ticket_id FROM exit_ticket_submissions")).fetchall():
        rows = conn.execute(
            sa.text("SELECT id, qtype, prompt, marks, data FROM exit_ticket_questions WHERE ticket_id = :t ORDER BY position"),
            {"t": tid}).fetchall()
        snapshot = {"version": 1, "questions": [
            {"id": r[0], "qtype": r[1], "prompt": r[2], "marks": r[3], "data": json.loads(r[4] or "{}")} for r in rows]}
        conn.execute(sa.text("UPDATE exit_ticket_submissions SET snapshot = :s, ticket_version = 1 WHERE id = :i"),
                     {"s": json.dumps(snapshot), "i": sid})


def downgrade():
    with op.batch_alter_table('exit_ticket_submissions') as batch:
        batch.drop_column('ticket_version')
        batch.drop_column('snapshot')
    with op.batch_alter_table('exit_ticket_questions') as batch:
        batch.drop_column('active')
    with op.batch_alter_table('exit_tickets') as batch:
        batch.drop_column('version')
