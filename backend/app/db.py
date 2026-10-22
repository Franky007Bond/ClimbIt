from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import MetaData

metadata = MetaData()

POSTGIS_CATALOG_TABLES = frozenset(
    {
        "spatial_ref_sys",
        "geometry_columns",
        "geography_columns",
        "raster_columns",
        "raster_overviews",
    }
)


def sqlalchemy_url(database_url: str) -> URL:
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        return url.set(drivername="postgresql+psycopg")
    return url


def create_engine_from_database_url(database_url: str) -> Engine:
    return create_engine(sqlalchemy_url(database_url))


def create_sessionmaker(database_url: str) -> sessionmaker:
    return sessionmaker(bind=create_engine_from_database_url(database_url))


def include_name(name, type_, parent_names) -> bool:
    if type_ == "table":
        return name in metadata.tables
    return True


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    if type_ == "table" and name in POSTGIS_CATALOG_TABLES:
        return False
    if type_ == "table" and reflected and name not in metadata.tables:
        return False
    return True
