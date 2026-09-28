"""add_user_is_active

Revision ID: a3f1c9d2e7b4
Revises: 6013810afdee
Create Date: 2026-09-28 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9d2e7b4'
down_revision: Union[str, Sequence[str], None] = '6013810afdee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # create_all() 建立的資料庫可能已經有這個欄位
    columns = [c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")]
    if "is_active" not in columns:
        op.add_column(
            "users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    op.drop_column("users", "is_active")
