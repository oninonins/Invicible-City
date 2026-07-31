"""baseline: existing schema at Alembic adoption

Reproduces the production `sdgs` schema exactly (verified via schema diff):

- 8 tables: user, province, city, district, village, facility, etl_job, dataset_metadata
- GiST indexes on geometry columns (idx_*_geom) - created by ETL, NOT declared in models
- facility.raw_tags is JSONB (production reality; model declares JSON)
- facility.source has server default 'OSM' (production reality)
- NO FK constraints on facility.city_id / facility.district_id (production has none;
  models declare FKs that were never applied to the database)

Applies to a FRESH database. On existing databases use `alembic stamp head`
(this baseline is the reference representation; no DDL runs against existing tables).

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_id", "user", ["id"], unique=False)
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_index("ix_user_full_name", "user", ["full_name"], unique=False)

    op.create_table(
        "province",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_province_id", "province", ["id"], unique=False)
    op.create_index("ix_province_code", "province", ["code"], unique=True)
    op.create_index("ix_province_name", "province", ["name"], unique=False)
    op.create_index("idx_province_geom", "province", ["geom"], unique=False, postgresql_using="gist")

    op.create_table(
        "city",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("province_id", sa.Integer(), nullable=True),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True),
        sa.ForeignKeyConstraint(["province_id"], ["province.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_city_id", "city", ["id"], unique=False)
    op.create_index("ix_city_code", "city", ["code"], unique=True)
    op.create_index("ix_city_name", "city", ["name"], unique=False)
    op.create_index("idx_city_geom", "city", ["geom"], unique=False, postgresql_using="gist")

    op.create_table(
        "district",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["city.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_district_id", "district", ["id"], unique=False)
    op.create_index("ix_district_code", "district", ["code"], unique=True)
    op.create_index("ix_district_name", "district", ["name"], unique=False)
    op.create_index("idx_district_geom", "district", ["geom"], unique=False, postgresql_using="gist")

    op.create_table(
        "village",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("village_type", sa.String(), nullable=True),
        sa.Column("bps_code", sa.String(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True),
        sa.ForeignKeyConstraint(["district_id"], ["district.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_village_id", "village", ["id"], unique=False)
    op.create_index("ix_village_code", "village", ["code"], unique=True)
    op.create_index("ix_village_name", "village", ["name"], unique=False)
    op.create_index("ix_village_bps_code", "village", ["bps_code"], unique=False)
    op.create_index("idx_village_geom", "village", ["geom"], unique=False, postgresql_using="gist")

    op.create_table(
        "facility",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("facility_type", sa.String(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("geom", geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), server_default="OSM", nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("raw_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_facility_id", "facility", ["id"], unique=False)
    op.create_index("ix_facility_name", "facility", ["name"], unique=False)
    op.create_index("ix_facility_facility_type", "facility", ["facility_type"], unique=False)
    op.create_index("idx_facility_district", "facility", ["district_id"], unique=False)
    op.create_index("idx_facility_source_eid", "facility", ["source", "external_id"], unique=True)
    op.create_index("idx_facility_type_city", "facility", ["facility_type", "city_id"], unique=False)
    op.create_index("idx_facility_geom", "facility", ["geom"], unique=False, postgresql_using="gist")

    op.create_table(
        "etl_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_name", sa.String(), nullable=False),
        sa.Column("data_source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("metadata_info", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_etl_job_id", "etl_job", ["id"], unique=False)
    op.create_index("ix_etl_job_city_name", "etl_job", ["city_name"], unique=False)

    op.create_table(
        "dataset_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("layer_name", sa.String(), nullable=False),
        sa.Column("download_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_metadata_id", "dataset_metadata", ["id"], unique=False)
    op.create_index("ix_dataset_metadata_layer_name", "dataset_metadata", ["layer_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dataset_metadata_layer_name", table_name="dataset_metadata")
    op.drop_index("ix_dataset_metadata_id", table_name="dataset_metadata")
    op.drop_table("dataset_metadata")

    op.drop_index("ix_etl_job_city_name", table_name="etl_job")
    op.drop_index("ix_etl_job_id", table_name="etl_job")
    op.drop_table("etl_job")

    op.drop_index("idx_facility_geom", table_name="facility")
    op.drop_index("idx_facility_type_city", table_name="facility")
    op.drop_index("idx_facility_source_eid", table_name="facility")
    op.drop_index("idx_facility_district", table_name="facility")
    op.drop_index("ix_facility_facility_type", table_name="facility")
    op.drop_index("ix_facility_name", table_name="facility")
    op.drop_index("ix_facility_id", table_name="facility")
    op.drop_table("facility")

    op.drop_index("idx_village_geom", table_name="village")
    op.drop_index("ix_village_bps_code", table_name="village")
    op.drop_index("ix_village_name", table_name="village")
    op.drop_index("ix_village_code", table_name="village")
    op.drop_index("ix_village_id", table_name="village")
    op.drop_table("village")

    op.drop_index("idx_district_geom", table_name="district")
    op.drop_index("ix_district_name", table_name="district")
    op.drop_index("ix_district_code", table_name="district")
    op.drop_index("ix_district_id", table_name="district")
    op.drop_table("district")

    op.drop_index("idx_city_geom", table_name="city")
    op.drop_index("ix_city_name", table_name="city")
    op.drop_index("ix_city_code", table_name="city")
    op.drop_index("ix_city_id", table_name="city")
    op.drop_table("city")

    op.drop_index("idx_province_geom", table_name="province")
    op.drop_index("ix_province_name", table_name="province")
    op.drop_index("ix_province_code", table_name="province")
    op.drop_index("ix_province_id", table_name="province")
    op.drop_table("province")

    op.drop_index("ix_user_full_name", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_index("ix_user_id", table_name="user")
    op.drop_table("user")
