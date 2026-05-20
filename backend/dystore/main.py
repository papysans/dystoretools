from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from dystore import __version__
from dystore.api.v1 import alerts as alerts_api
from dystore.api.v1 import auth as auth_api
from dystore.api.v1 import comments as comments_api
from dystore.api.v1 import compass as compass_api
from dystore.api.v1 import content as content_api
from dystore.api.v1 import orders as orders_api
from dystore.api.v1 import peer as peer_api
from dystore.api.v1 import scrape as scrape_api
from dystore.api.v1 import settings as settings_api
from dystore.core.config import get_settings
from dystore.core.logging import configure_logging, get_logger
from dystore.scheduler.scheduler import shutdown_scheduler, start_scheduler
from dystore.ws.endpoints import router as ws_router

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info(
        "dystore.start",
        version=__version__,
        settings=get_settings().model_dump(
            exclude={"mysql_password", "deepseek_api_key", "kimi_api_key", "huitu_api_key", "chanmama_api_key"}
        ),
    )
    start_scheduler()
    yield
    shutdown_scheduler()
    log.info("dystore.stop")


app = FastAPI(title="dystoretools", version=__version__, lifespan=lifespan)

app.include_router(auth_api.router)
app.include_router(scrape_api.router)
app.include_router(orders_api.router)
app.include_router(comments_api.router)
app.include_router(content_api.router)
app.include_router(compass_api.router)
app.include_router(peer_api.router)
app.include_router(alerts_api.router)
app.include_router(settings_api.router)
app.include_router(ws_router)


@app.get("/api/v1/system/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
async def health_alias() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/system/version")
async def version() -> dict[str, str]:
    return {"version": __version__}
