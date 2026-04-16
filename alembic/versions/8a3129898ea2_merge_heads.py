"""merge heads

Revision ID: 8a3129898ea2
Revises: 3b73af33a7d1, s7t8u9v0w1x2
Create Date: 2026-04-16 13:43:35.474801
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a3129898ea2'
down_revision: Union[str, None] = ('3b73af33a7d1', 's7t8u9v0w1x2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
