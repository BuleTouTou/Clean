"""Create PostgreSQL report and application-setting tables."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_postgresql_storage"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column("entrust_date", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blocking_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("audit_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_object_key", sa.Text(), nullable=True),
        sa.Column("output_file", sa.Text(), nullable=True),
        sa.Column("output_url", sa.Text(), nullable=True),
        sa.Column("output_object_key", sa.Text(), nullable=True),
        sa.Column("report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", name="uq_task_reports_task_id"),
    )
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("task_reports")
