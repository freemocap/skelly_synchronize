import logging
import multiprocessing

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from skelly_synchronize.api.routers import health, jobs, videos
from skelly_synchronize.core.exceptions import (
    BackendSubprocessError,
    SkellySyncError,
    VideoProbeError,
)
from skelly_synchronize.core.logging_setup import configure_logging

_LOCALHOST_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app = FastAPI(title="skelly_synchronize API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=_LOCALHOST_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(videos.router)
app.include_router(jobs.router)


@app.exception_handler(SkellySyncError)
def handle_skelly_sync_error(request: Request, exc: SkellySyncError) -> JSONResponse:
    if isinstance(exc, VideoProbeError):
        status_code = 422
    elif isinstance(exc, BackendSubprocessError):
        return JSONResponse(
            status_code=500, content={"detail": str(exc), "stderr": exc.stderr}
        )
    else:
        status_code = 500
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


def run() -> None:
    multiprocessing.freeze_support()

    import uvicorn

    configure_logging(level=logging.INFO)
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
