"""ufs: add ufs_indicators and ufs_scores tables

Adds the UFS v0 persistence layer:

- `ufs_indicators`: per-indicator config + empirically derived benchmarks
  (median density over nonzero districts) and the accessibility reference
  distance (1 km, Euclidean proxy).
- `ufs_scores`: cached UFS results per scope (district | city).

Revision ID: 0002_ufs
Revises: 0001_baseline
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ufs"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ufs_indicators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("indicator", sa.String(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("benchmark_density", sa.Float(), nullable=True),
        sa.Column("reference_km", sa.Float(), nullable=True),
        sa.Column("benchmark_note", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ufs_indicators_id", "ufs_indicators", ["id"], unique=False)
    op.create_index("ix_ufs_indicators_indicator", "ufs_indicators", ["indicator"], unique=True)

    op.create_table(
        "ufs_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("indicators", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_facilities", sa.Integer(), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("district_count", sa.Integer(), nullable=False),
        sa.Column("methodology", sa.String(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_type", "scope_id", name="uq_ufs_scope"),
    )
    op.create_index("ix_ufs_scores_id", "ufs_scores", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ufs_scores_id", table_name="ufs_scores")
    op.drop_table("ufs_scores")

    op.drop_index("ix_ufs_indicators_indicator", table_name="ufs_indicators")
    op.drop_index("ix_ufs_indicators_id", table_name="ufs_indicators")
    op.drop_table("ufs_indicators")
