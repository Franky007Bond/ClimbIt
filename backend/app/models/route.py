import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db import metadata


class Base(DeclarativeBase):
    metadata = metadata


class RouteRecord(Base):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    route_type: Mapped[str] = mapped_column(Text, nullable=False)
    region_name: Mapped[str] = mapped_column(Text, nullable=False)
    region_country: Mapped[str] = mapped_column(Text, nullable=False)
    region_coverage: Mapped[str] = mapped_column(Text, nullable=False)
    publication: Mapped[str] = mapped_column(Text, nullable=False)
    trailhead: Mapped[WKBElement | None] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            dimension=2,
            spatial_index=False,
        ),
        nullable=True,
    )
    linestring: Mapped[WKBElement | None] = mapped_column(
        Geometry(
            geometry_type="LINESTRING",
            srid=4326,
            dimension=2,
            spatial_index=False,
        ),
        nullable=True,
    )
    gpx: Mapped[str | None] = mapped_column(Text, nullable=True)
    elevation_min_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elevation_max_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elevation_gain_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elevation_loss_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approach_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    technical_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    original_difficulty_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_difficulty_scale: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_route_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_original_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_original_scale: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_structured_scale: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_structured_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_mapped_huebler: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_mapping_confidence: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    difficulty_mapping_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_mapping_citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_mapping_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_review_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    closure_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closure_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closure_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closure_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    season_months: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    season_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    transit_accessibility: Mapped[str] = mapped_column(Text, nullable=False)
    official_source_links: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    provenance: Mapped[str] = mapped_column(Text, nullable=False)
    completeness: Mapped[str] = mapped_column(Text, nullable=False)
    assessment: Mapped[str] = mapped_column(Text, nullable=False)
