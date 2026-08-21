"""add_loan_table

Revision ID: 61d693b4777d
Revises: 77df0175ac82
Create Date: 2026-08-21 20:09:57.774063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61d693b4777d'
down_revision: Union[str, Sequence[str], None] = '77df0175ac82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'loans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('lender_id', sa.UUID(), nullable=False),
        sa.Column('borrower_id', sa.UUID(), nullable=False),
        sa.Column('principal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('outstanding', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('repaid_at', sa.DateTime(), nullable=True),
        sa.Column('written_off_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['borrower_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['lender_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('loans')
