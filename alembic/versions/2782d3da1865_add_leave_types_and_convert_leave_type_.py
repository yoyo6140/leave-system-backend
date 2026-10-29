"""add leave_types and convert leave type to code

Revision ID: 2782d3da1865
Revises: a3f1c9d2e7b4
Create Date: 2026-10-29 22:35:03.748652

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2782d3da1865'
down_revision: Union[str, Sequence[str], None] = 'a3f1c9d2e7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ↓ 從這裡開始是新加的
LEAVE_TYPES = [
    # code,          name,  quota_type,  quota_hours, sort_order
    ("annual",      "特休", "seniority", None, 1),
    ("sick",        "病假", "fixed",     240,  2),
    ("personal",    "事假", "fixed",     112,  3),
    ("marriage",    "婚假", "unlimited", None, 4),
    ("bereavement", "喪假", "unlimited", None, 5),
    ("official",    "公假", "unlimited", None, 6),
    ("other",       "其他", "unlimited", None, 7),
]

OLD_ENUM_NAME = "leave_type"
OLD_ENUM_VALUES = ("特休", "病假", "事假", "婚假", "喪假", "公假", "其他")

# 中文 ←→ 英文代碼 對照表，upgrade/downgrade 都會用到
CODE_BY_NAME = {name: code for code, name, *_ in LEAVE_TYPES}
NAME_BY_CODE = {code: name for code, name, *_ in LEAVE_TYPES}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) 建立 leave_types 表
    #    create_all() 可能在這支 migration 跑之前就已經照新 model 建過表了（dev 環境每次
    #    啟動都會跑 create_all），所以先檢查一下，不要重複建表。
    if "leave_types" not in inspector.get_table_names():
        leave_types_table = op.create_table(
            "leave_types",
            sa.Column("code", sa.String(20), primary_key=True),
            sa.Column("name", sa.String(20), nullable=False),
            sa.Column("quota_type", sa.String(20), nullable=False),
            sa.Column("quota_hours", sa.Integer(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False),
        )
    else:
        leave_types_table = sa.table(
            "leave_types",
            sa.column("code"),
            sa.column("name"),
            sa.column("quota_type"),
            sa.column("quota_hours"),
            sa.column("sort_order"),
        )

    # 2) 塞種子資料（7 種假別）——同理，已經有資料就不要重複塞
    row_count = bind.execute(sa.text("SELECT COUNT(*) FROM leave_types")).scalar()
    if not row_count:
        op.bulk_insert(
            leave_types_table,
            [
                {
                    "code": code,
                    "name": name,
                    "quota_type": quota_type,
                    "quota_hours": quota_hours,
                    "sort_order": sort_order,
                }
                for code, name, quota_type, quota_hours, sort_order in LEAVE_TYPES
            ],
        )

    # 3) 判斷 leave_records.type 現在是不是還是舊的中文 Enum：
    #    - 在還有舊資料的環境（現在的 AWS RDS、之後的 Render）：是 Enum，要完整走型別轉換
    #      + 資料轉換 + 清掉舊 enum type。
    #    - 在剛被 create_all() 建出來的全新資料庫：型別已經直接是 VARCHAR，這幾步全部跳過。
    existing_columns = {c["name"]: c for c in inspector.get_columns("leave_records")}
    type_is_old_enum = isinstance(existing_columns["type"]["type"], sa.Enum)

    if type_is_old_enum:
        op.alter_column(
            "leave_records",
            "type",
            existing_type=sa.Enum(*OLD_ENUM_VALUES, name=OLD_ENUM_NAME),
            type_=sa.String(20),
            existing_nullable=False,
            postgresql_using="type::text",
        )

        case_sql = " ".join(
            f"WHEN '{name}' THEN '{code}'" for name, code in CODE_BY_NAME.items()
        )
        op.execute(f"UPDATE leave_records SET type = CASE type {case_sql} END")
        op.execute(f"DROP TYPE IF EXISTS {OLD_ENUM_NAME}")

    # 4) 不管上面走哪條路，都要確保 FK 存在
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("leave_records")}
    if "fk_leave_records_type_leave_types" not in existing_fks:
        op.create_foreign_key(
            "fk_leave_records_type_leave_types",
            "leave_records",
            "leave_types",
            ["type"],
            ["code"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    # 反向操作：先拿掉 FK
    op.drop_constraint(
        "fk_leave_records_type_leave_types", "leave_records", type_="foreignkey"
    )

    # 把英文代碼轉回中文
    case_sql = " ".join(
        f"WHEN '{code}' THEN '{name}'" for code, name in NAME_BY_CODE.items()
    )
    op.execute(f"UPDATE leave_records SET type = CASE type {case_sql} END")

    # 重新建立 enum type，把欄位型別換回去
    leave_type_enum = sa.Enum(*OLD_ENUM_VALUES, name=OLD_ENUM_NAME)
    leave_type_enum.create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "leave_records",
        "type",
        existing_type=sa.String(20),
        type_=leave_type_enum,
        existing_nullable=False,
        postgresql_using=f"type::{OLD_ENUM_NAME}",
    )

    # 刪掉 leave_types 表
    op.drop_table("leave_types")
