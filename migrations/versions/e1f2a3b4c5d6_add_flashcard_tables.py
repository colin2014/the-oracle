"""Add flashcard sets, cards, assignments and progress tables

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
Create Date: 2026-07-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('flashcard_sets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('book_folder', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flashcard_sets_book_folder'), 'flashcard_sets', ['book_folder'], unique=False)

    op.create_table('flashcards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('set_id', sa.Integer(), nullable=False),
    sa.Column('page_id', sa.String(length=50), nullable=True),
    sa.Column('term', sa.Text(), nullable=False),
    sa.Column('definition', sa.Text(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['set_id'], ['flashcard_sets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flashcards_set_id'), 'flashcards', ['set_id'], unique=False)

    op.create_table('flashcard_assignments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('set_id', sa.Integer(), nullable=False),
    sa.Column('class_id', sa.Integer(), nullable=True),
    sa.Column('student_id', sa.Integer(), nullable=True),
    sa.Column('due_date', sa.DateTime(), nullable=True),
    sa.Column('assigned_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['set_id'], ['flashcard_sets.id'], ),
    sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flashcard_assignments_set_id'), 'flashcard_assignments', ['set_id'], unique=False)
    op.create_index(op.f('ix_flashcard_assignments_class_id'), 'flashcard_assignments', ['class_id'], unique=False)
    op.create_index(op.f('ix_flashcard_assignments_student_id'), 'flashcard_assignments', ['student_id'], unique=False)

    op.create_table('flashcard_progress',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('card_id', sa.Integer(), nullable=False),
    sa.Column('student_id', sa.Integer(), nullable=False),
    sa.Column('correct_count', sa.Integer(), nullable=False),
    sa.Column('incorrect_count', sa.Integer(), nullable=False),
    sa.Column('last_correct', sa.Boolean(), nullable=True),
    sa.Column('last_reviewed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['card_id'], ['flashcards.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('card_id', 'student_id', name='uq_flashcard_progress_student')
    )
    op.create_index(op.f('ix_flashcard_progress_card_id'), 'flashcard_progress', ['card_id'], unique=False)
    op.create_index(op.f('ix_flashcard_progress_student_id'), 'flashcard_progress', ['student_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_flashcard_progress_student_id'), table_name='flashcard_progress')
    op.drop_index(op.f('ix_flashcard_progress_card_id'), table_name='flashcard_progress')
    op.drop_table('flashcard_progress')
    op.drop_index(op.f('ix_flashcard_assignments_student_id'), table_name='flashcard_assignments')
    op.drop_index(op.f('ix_flashcard_assignments_class_id'), table_name='flashcard_assignments')
    op.drop_index(op.f('ix_flashcard_assignments_set_id'), table_name='flashcard_assignments')
    op.drop_table('flashcard_assignments')
    op.drop_index(op.f('ix_flashcards_set_id'), table_name='flashcards')
    op.drop_table('flashcards')
    op.drop_index(op.f('ix_flashcard_sets_book_folder'), table_name='flashcard_sets')
    op.drop_table('flashcard_sets')
