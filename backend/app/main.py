import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.plans import router as plans_router
from app.api.shares import router as shares_router
from app.api.trips import router as trips_router
from app.api.maintainer import router as maintainer_router
from app.api.maintainer_revisions import router as maintainer_revisions_router
from app.api.routes import router as routes_router
from app.health import health_body, ready_response
from app.json_logging import configure_logging, log_http_access
from app.telemetry.middleware import trace_plan_http_requests
from app.telemetry.tracing import configure_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    configure_tracing()
    yield


configure_logging()
app = FastAPI(title="ClimbIt", lifespan=lifespan)

_default_cors_origins = "http://127.0.0.1:5173,http://localhost:5173"
_cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", _default_cors_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.middleware("http")(log_http_access)
app.middleware("http")(trace_plan_http_requests)
app.include_router(routes_router)
app.include_router(plans_router)
app.include_router(trips_router)
app.include_router(shares_router)
app.include_router(maintainer_router)
app.include_router(maintainer_revisions_router)


@app.get("/health")
def health():
    return health_body()


@app.get("/ready")
def ready():
    return ready_response()
