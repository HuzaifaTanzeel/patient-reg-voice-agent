import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.database import engine
from backend.app.routes.patients import router as patients_router

logger = logging.getLogger("patient_reg")


def configure_logging() -> None:
    logger.setLevel(logging.INFO)
    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        logger.addHandler(handler)
    logger.propagate = False


configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Patient Registration API", version="0.1.0", lifespan=lifespan)
# Temporarily permissive so a local dashboard can call the API.
# Lock this down to the React dashboard's real deployed origin once that URL exists.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(patients_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}



def _json_safe(value: object) -> object:
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _error_body(detail: object) -> dict:
    return {"data": None, "error": {"detail": _json_safe(detail)}}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content=_error_body(exc.errors()))


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc.detail))


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc.detail))


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error: %s", exc)
    return JSONResponse(
        status_code=500, content=_error_body("Internal server error")
    )
