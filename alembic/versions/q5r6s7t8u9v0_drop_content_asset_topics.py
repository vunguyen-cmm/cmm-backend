"""Drop content_asset_topics table — topics are now linked via topic_resources.

Revision ID: q5r6s7t8u9v0
Revises: o3p4q5r6s7t8
Create Date: 2026-04-13
"""

from alembic import op


revision = "q5r6s7t8u9v0"
down_revision = "o3p4q5r6s7t8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("content_asset_topics")


def downgrade() -> None:
    import sqlalchemy as sa

    op.create_table(
        "content_asset_topics",
        sa.Column("content_asset_id", sa.Uuid(), sa.ForeignKey("content_assets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("topic_id", sa.Uuid(), sa.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
