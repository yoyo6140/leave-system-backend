"""make_user_fields_required

Revision ID: 6013810afdee
Revises: 
Create Date: 2026-05-26 00:22:53.263987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6013810afdee'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先把現有的 NULL 填上預設值，才能改成 NOT NULL
    op.execute("UPDATE users SET email = 'unknown@unknown.com' WHERE email IS NULL")
    op.execute("UPDATE users SET gender = '男' WHERE gender IS NULL")
    op.execute("UPDATE users SET id_number = 'UNKNOWN' WHERE id_number IS NULL")
    op.execute("UPDATE users SET hire_date = '1970-01-01' WHERE hire_date IS NULL")
    op.execute("UPDATE users SET birth_date = '1970-01-01' WHERE birth_date IS NULL")

    # 改成 NOT NULL
    op.alter_column("users", "email",      nullable=False)
    op.alter_column("users", "gender",     nullable=False)
    op.alter_column("users", "id_number",  nullable=False)
    op.alter_column("users", "hire_date",  nullable=False)
    op.alter_column("users", "birth_date", nullable=False)


def downgrade() -> None:
    # 還原成允許 NULL
    op.alter_column("users", "email",      nullable=True)
    op.alter_column("users", "gender",     nullable=True)
    op.alter_column("users", "id_number",  nullable=True)
    op.alter_column("users", "hire_date",  nullable=True)
    op.alter_column("users", "birth_date", nullable=True)
