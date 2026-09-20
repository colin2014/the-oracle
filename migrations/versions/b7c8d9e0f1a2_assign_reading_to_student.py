"""Allow reading assignments to target an individual student

Adds a nullable ``student_id`` foreign key to ``reading_assignments`` and makes
``class_id`` nullable so an assignment can target either a whole class or a
single student.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('reading_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('student_id', sa.Integer(), nullable=True))
        batch_op.alter_column('class_id', existing_type=sa.Integer(), nullable=True)
        batch_op.create_index('ix_reading_assignments_student_id', ['student_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_reading_assignments_student_id_users',
            'users', ['student_id'], ['id'],
        )


def downgrade():
    with op.batch_alter_table('reading_assignments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_reading_assignments_student_id_users', type_='foreignkey')
        batch_op.drop_index('ix_reading_assignments_student_id')
        batch_op.alter_column('class_id', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column('student_id')
