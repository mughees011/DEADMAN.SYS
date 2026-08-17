"""Add baseline cols to system_state

Revision ID: 77df0175ac82
Revises: b1aaec129bef
Create Date: 2026-08-17 19:12:08.844051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77df0175ac82'
down_revision: Union[str, Sequence[str], None] = 'b1aaec129bef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('system_state', sa.Column('alpaca_cash_baseline', sa.Float(), nullable=True))
    op.add_column('system_state', sa.Column('agents_balance_baseline', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('system_state', 'agents_balance_baseline')
    op.drop_column('system_state', 'alpaca_cash_baseline')
