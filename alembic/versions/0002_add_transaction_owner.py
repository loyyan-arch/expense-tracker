"""add transaction owner

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09 22:10:15.189725

"""
"""为账单添加所属用户，并处理已有账单。"""

from alembic import context, op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    count = connection.execute(
        sa.text("SELECT COUNT(*) FROM transactions")
    ).scalar_one()

    owner_id = None

    # 只有存在旧账单时，才需要指定它们的归属。
    if count > 0:
        arguments = context.get_x_argument(as_dictionary=True)
        username = arguments.get("legacy_owner")

        if not username:
            raise RuntimeError(
                "存在旧账单，请通过 -x legacy_owner=用户名 指定归属"
            )

        owner_id = connection.execute(
            sa.text(
                "SELECT id FROM users WHERE username = :username"
            ),
            {"username": username},
        ).scalar_one_or_none()

        if owner_id is None:
            raise RuntimeError("指定的账单归属用户不存在")

    # 先添加可空列，让现有记录能保留下来。
    op.add_column(
        "transactions",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )

    if count > 0:
        connection.execute(
            sa.text(
                "UPDATE transactions "
                "SET user_id = :owner_id "
                "WHERE user_id IS NULL"
            ),
            {"owner_id": owner_id},
        )

    # 数据回填完成后，再设置最终约束。
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_transactions_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_transactions_user_id",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_index("ix_transactions_user_id")
        batch_op.drop_constraint(
            "fk_transactions_user_id_users",
            type_="foreignkey",
        )
        batch_op.drop_column("user_id")