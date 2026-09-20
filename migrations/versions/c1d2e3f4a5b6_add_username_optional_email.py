"""add username, make email optional

Revision ID: c1d2e3f4a5b6
Revises: b8bf8d2e0be7
Create Date: 2026-07-16

Adds a `username` login handle and relaxes `email` to be optional. Uses batch
mode so SQLite can rebuild the table (column add + nullability change + unique
index). Existing rows get a username backfilled from their email local-part.
"""
from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "b8bf8d2e0be7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(length=80), nullable=True))
        batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=True)
        batch_op.create_index(batch_op.f("ix_users_username"), ["username"], unique=True)

    # Backfill username from the email local-part (lowercased, de-duplicated)
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, email FROM users WHERE username IS NULL")).fetchall()
    taken = set()
    for uid, email in rows:
        base = ((email or f"user{uid}").split("@")[0]).strip().lower() or f"user{uid}"
        candidate, n = base, 2
        while candidate in taken:
            candidate, n = f"{base}{n}", n + 1
        taken.add(candidate)
        conn.execute(sa.text("UPDATE users SET username = :u WHERE id = :id"), {"u": candidate, "id": uid})


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_username"))
        batch_op.alter_column("email", existing_type=sa.String(length=255), nullable=False)
        batch_op.drop_column("username")
