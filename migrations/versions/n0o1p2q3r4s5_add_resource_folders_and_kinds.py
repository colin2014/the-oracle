"""Generalise slide_decks into resources (kind + folder), add resource_folders

Revision ID: n0o1p2q3r4s5
Revises: m9n0o1p2q3r4
Create Date: 2026-07-31

The library now holds more than PowerPoints (video/pdf/worksheet links), and
supports teacher-made folders nested inside a unit alongside the syllabus
subsections. slide_decks is renamed rather than recreated so existing rows
(and their ids, referenced nowhere else) survive untouched.
"""
from alembic import op
import sqlalchemy as sa


revision = 'n0o1p2q3r4s5'
down_revision = 'm9n0o1p2q3r4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'resource_folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scope', sa.String(length=40), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['resource_folders.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('resource_folders', schema=None) as batch_op:
        batch_op.create_index('ix_resource_folders_scope', ['scope'])
        batch_op.create_index('ix_resource_folders_parent_id', ['parent_id'])

    op.rename_table('slide_decks', 'resources')
    with op.batch_alter_table('resources', schema=None) as batch_op:
        batch_op.add_column(sa.Column('kind', sa.String(length=20), nullable=False, server_default='deck'))
        batch_op.add_column(sa.Column('folder_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_resources_folder_id', ['folder_id'])
        batch_op.create_foreign_key('fk_resources_folder_id', 'resource_folders', ['folder_id'], ['id'])


def downgrade():
    with op.batch_alter_table('resources', schema=None) as batch_op:
        batch_op.drop_constraint('fk_resources_folder_id', type_='foreignkey')
        batch_op.drop_index('ix_resources_folder_id')
        batch_op.drop_column('folder_id')
        batch_op.drop_column('kind')
    op.rename_table('resources', 'slide_decks')

    with op.batch_alter_table('resource_folders', schema=None) as batch_op:
        batch_op.drop_index('ix_resource_folders_parent_id')
        batch_op.drop_index('ix_resource_folders_scope')
    op.drop_table('resource_folders')
