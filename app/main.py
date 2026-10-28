from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.exceptions import LedgerError, ledger_error_handler, validation_error_handler
from app.routers import accounts, transactions, transfers
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Backend API for a simple transaction ledger.",
    version="1.0.0",
    lifespan=lifespan,
    redoc_url=None,
)

app.add_exception_handler(LedgerError, ledger_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(transfers.router)


@app.get("/redoc", include_in_schema=False)
def redoc() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
        with_google_fonts=False,
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
