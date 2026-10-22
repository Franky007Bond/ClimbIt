from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as routes_router
from app.health import health_body, ready_response
from app.json_logging import configure_logging, log_http_access


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


configure_logging()
app = FastAPI(title="ClimbIt", lifespan=lifespan)
app.middleware("http")(log_http_access)
app.include_router(routes_router)


@app.get("/health")
def health():
    return health_body()


@app.get("/ready")
def ready():
    return ready_response()
