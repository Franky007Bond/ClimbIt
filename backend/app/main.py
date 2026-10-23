import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as routes_router
from app.health import health_body, ready_response
from app.json_logging import configure_logging, log_http_access


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
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
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.middleware("http")(log_http_access)
app.include_router(routes_router)


@app.get("/health")
def health():
    return health_body()


@app.get("/ready")
def ready():
    return ready_response()
