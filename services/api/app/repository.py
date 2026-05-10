from json import JSONDecodeError, loads
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .schemas import DemoScene, QualityReport, SceneMetadata

ModelType = TypeVar("ModelType", bound=BaseModel)


class SceneNotFoundError(Exception):
    pass


class SceneDataError(Exception):
    pass


class SceneRepository:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root

    def list_demo_scenes(self) -> list[DemoScene]:
        registry = self._read_json(self.data_root / "demo-scenes.json")
        if not isinstance(registry, list):
            raise SceneDataError("Demo scene registry must be a list")

        return [self._validate_model(DemoScene, item) for item in registry]

    def get_scene_metadata(self, scene_id: str) -> SceneMetadata:
        self._assert_registered_scene(scene_id)
        return self._read_model(self._scene_root(scene_id) / "metadata.json", SceneMetadata)

    def get_quality_report(self, scene_id: str) -> QualityReport:
        self._assert_registered_scene(scene_id)
        return self._read_model(self._scene_root(scene_id) / "quality.json", QualityReport)

    def scene_exists(self, scene_id: str) -> bool:
        return any(scene.scene_id == scene_id for scene in self.list_demo_scenes())

    def _assert_registered_scene(self, scene_id: str) -> None:
        if not self.scene_exists(scene_id):
            raise SceneNotFoundError(scene_id)

    def _scene_root(self, scene_id: str) -> Path:
        return self.data_root / "scenes" / scene_id

    def _read_model(self, path: Path, model_type: type[ModelType]) -> ModelType:
        return self._validate_model(model_type, self._read_json(path))

    def _read_json(self, path: Path) -> object:
        try:
            return loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise SceneDataError(f"Missing scene data file: {path}") from error
        except JSONDecodeError as error:
            raise SceneDataError(f"Invalid JSON in scene data file: {path}") from error

    def _validate_model(self, model_type: type[ModelType], payload: object) -> ModelType:
        try:
            return model_type.model_validate(payload)
        except ValidationError as error:
            raise SceneDataError(str(error)) from error
