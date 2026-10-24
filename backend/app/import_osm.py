from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime
from datetime import timezone

from sqlalchemy.orm import Session

from app.db import create_sessionmaker
from app.domain.route import Publication
from app.domain.route import Provenance
from app.models.route import RouteRecord
from app.osm.geometry import OsmGeometryError
from app.osm.geometry import parse_overpass_geometry
from app.osm.import_route import build_osm_import_route
from app.osm.import_route import osm_route_id
from app.osm.manifest import ImportManifest
from app.osm.manifest import load_manifest
from app.osm.overpass import OverpassClient
from app.osm.overpass import UrllibOverpassClient
from app.osm.overpass import overpass_api_url
from app.osm.overpass import overpass_min_interval_seconds
from app.repositories.routes import upsert_route

logger = logging.getLogger(__name__)


class OsmImportConflictError(Exception):
    def __init__(self, entry_label: str) -> None:
        self.entry_label = entry_label
        super().__init__(f"import conflict for {entry_label}")


def _ensure_import_allowed(session: Session, route_id: uuid.UUID, entry_label: str) -> None:
    existing = session.get(RouteRecord, route_id)
    if existing is None:
        return
    if (
        existing.provenance == Provenance.OSM.value
        and existing.publication == Publication.QUARANTINED.value
    ):
        return
    raise OsmImportConflictError(entry_label)


def import_osm_routes(
    session: Session,
    manifest: ImportManifest,
    *,
    overpass: OverpassClient,
    imported_at: datetime | None = None,
) -> list[uuid.UUID]:
    when = imported_at or datetime.now(timezone.utc)
    route_ids: list[uuid.UUID] = []
    for entry in manifest.entries:
        entry_label = f"{entry.osm_type.value}/{entry.osm_id}"
        route_id = osm_route_id(entry.osm_type.value, entry.osm_id)
        _ensure_import_allowed(session, route_id, entry_label)

        payload = overpass.fetch_element(entry.osm_type, entry.osm_id)
        geometry = parse_overpass_geometry(
            payload,
            osm_type=entry.osm_type.value,
            osm_id=entry.osm_id,
        )
        route = build_osm_import_route(entry=entry, geometry=geometry, imported_at=when)
        route_ids.append(
            upsert_route(session, route_id, route, author_kind="system"),
        )
    return route_ids


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Import OpenStreetMap routes into quarantine")
    parser.add_argument("--manifest", required=True, help="Path to JSON import manifest")
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL is not set")
        return 1

    try:
        manifest = load_manifest(args.manifest)
    except Exception as exc:
        logger.error("invalid manifest: %s", exc)
        return 1

    overpass: OverpassClient = UrllibOverpassClient(
        api_url=overpass_api_url(),
        min_interval_seconds=overpass_min_interval_seconds(),
    )

    SessionLocal = create_sessionmaker(database_url)
    session = SessionLocal()
    bind = session.get_bind()
    try:
        import_osm_routes(session, manifest, overpass=overpass)
        session.commit()
    except OsmImportConflictError as exc:
        session.rollback()
        print(exc.entry_label, file=sys.stderr)
        return 1
    except (OsmGeometryError, Exception):
        session.rollback()
        logger.exception("OSM import failed")
        return 1
    finally:
        session.close()
        bind.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
