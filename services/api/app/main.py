from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ApiSettings, default_settings
from .repository import SceneDataError, SceneNotFoundError, SceneRepository
from .routes import map_scene_errors, router


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved_settings = settings or default_settings()
    app = FastAPI(title="DreamNav API", version="0.1.0")
    app.state.settings = resolved_settings
    app.state.scene_repository = SceneRepository(resolved_settings.data_root)
    app.include_router(router)
    app.add_exception_handler(SceneNotFoundError, _scene_exception_handler)
    app.add_exception_handler(SceneDataError, _scene_exception_handler)

    if resolved_settings.scenes_root.exists():
        app.mount("/scenes", StaticFiles(directory=resolved_settings.scenes_root), name="scenes")

    return app


async def _scene_exception_handler(request: Request, error: Exception) -> JSONResponse:
    del request
    mapped_error = map_scene_errors(error)
    return JSONResponse(
        status_code=mapped_error.status_code,
        content={"detail": mapped_error.detail},
    )


app = create_app()
