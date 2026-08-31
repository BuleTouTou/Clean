"""Add users, sessions and report ownership."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002_users_and_report_ownership"
down_revision: str | None = "0001_postgresql_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.add_column("task_reports", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_task_reports_user_id_users",
        "task_reports",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_task_reports_user_id", "task_reports", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_task_reports_user_id", table_name="task_reports")
    op.drop_constraint("fk_task_reports_user_id_users", "task_reports", type_="foreignkey")
    op.drop_column("task_reports", "user_id")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("users")
