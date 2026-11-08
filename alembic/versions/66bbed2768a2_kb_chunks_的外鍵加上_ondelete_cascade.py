"""kb_chunks 的外鍵加上 ondelete CASCADE

Revision ID: 66bbed2768a2
Revises: 38695a92955f
Create Date: 2026-11-08 23:48:49.110550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66bbed2768a2'
down_revision: Union[str, Sequence[str], None] = '38695a92955f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('kb_chunks_document_id_fkey', 'kb_chunks', type_='foreignkey')
    op.create_foreign_key(
        'kb_chunks_document_id_fkey', 'kb_chunks', 'kb_documents',
        ['document_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('kb_chunks_document_id_fkey', 'kb_chunks', type_='foreignkey')
    op.create_foreign_key(
        'kb_chunks_document_id_fkey', 'kb_chunks', 'kb_documents',
        ['document_id'], ['id']
    )