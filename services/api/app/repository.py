from json import JSONDecodeError, loads
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .schemas import DemoReadiness, DemoScene, QualityReport, SceneAssetStatus, SceneMetadata

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

    def get_asset_status(self, scene_id: str) -> SceneAssetStatus:
        metadata = self.get_scene_metadata(scene_id)
        splat_path = self._scene_root(scene_id) / metadata.splat_file
        splat_available = splat_path.is_file()
        missing_assets = [] if splat_available else [metadata.splat_file]

        return SceneAssetStatus(
            scene_id=scene_id,
            splat_url=f"/scenes/{scene_id}/{metadata.splat_file}",
            splat_available=splat_available,
            viewer_render_mode="splat" if splat_available else "placeholder",
            missing_assets=missing_assets,
        )

    def get_demo_readiness(self, scene_id: str) -> DemoReadiness:
        metadata = self.get_scene_metadata(scene_id)
        quality = self.get_quality_report(scene_id)
        asset_status = self.get_asset_status(scene_id)
        required_assets = [
            "metadata.json",
            "quality.json",
            metadata.camera_path,
            "visibility_manifest.json",
            "completion_manifest.json",
            metadata.splat_file,
        ]
        missing_assets = [
            asset_name for asset_name in required_assets if not self._asset_exists(scene_id, asset_name)
        ]
        fallback_assets_present = self._cached_completion_assets_present(scene_id)
        blockers = self._readiness_blockers(missing_assets, quality.quality_gate)
        warnings = self._readiness_warnings(
            quality.quality_gate,
            quality.cached_completion,
            fallback_assets_present,
        )

        return DemoReadiness(
            scene_id=scene_id,
            locked_scene=True,
            required_assets_present=len(missing_assets) == 0,
            fallback_assets_present=fallback_assets_present,
            quality_gate=quality.quality_gate,
            cached_completion=quality.cached_completion,
            viewer_render_mode=asset_status.viewer_render_mode,
            status=self._readiness_status(blockers, warnings),
            blockers=blockers,
            warnings=warnings,
        )

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

    def _cached_completion_assets_present(self, scene_id: str) -> bool:
        manifest = self._read_json(self._scene_root(scene_id) / "completion_manifest.json")
        if not isinstance(manifest, dict):
            raise SceneDataError("Completion manifest must be an object")

        predictions = manifest.get("cached_predictions")
        if not isinstance(predictions, list) or len(predictions) == 0:
            return False

        asset_names: list[str] = []
        for prediction in predictions:
            if not isinstance(prediction, dict):
                raise SceneDataError("Cached completion predictions must be objects")

            for field_name in ("rgb_asset", "confidence_mask_asset", "nearest_view_asset"):
                asset_name = prediction.get(field_name)
                if isinstance(asset_name, str):
                    asset_names.append(asset_name)

        return len(asset_names) > 0 and all(
            self._asset_exists(scene_id, asset_name) for asset_name in asset_names
        )

    def _asset_exists(self, scene_id: str, asset_name: str) -> bool:
        asset_path = Path(asset_name)
        if asset_path.is_absolute() or ".." in asset_path.parts:
            raise SceneDataError(f"Unsafe scene asset path: {asset_name}")

        return (self._scene_root(scene_id) / asset_path).is_file()

    def _readiness_blockers(self, missing_assets: list[str], quality_gate: str) -> list[str]:
        blockers: list[str] = []
        if missing_assets:
            blockers.append(f"Missing required demo assets: {', '.join(missing_assets)}")

        if quality_gate == "fail":
            blockers.append("Quality gate failed.")

        return blockers

    def _readiness_warnings(
        self,
        quality_gate: str,
        cached_completion: bool,
        fallback_assets_present: bool,
    ) -> list[str]:
        warnings: list[str] = []
        if quality_gate == "warning":
            warnings.append("Completion must stay labeled as lower confidence.")

        if not cached_completion or not fallback_assets_present:
            warnings.append("Cached completion fallback assets unavailable.")

        return warnings

    def _readiness_status(self, blockers: list[str], warnings: list[str]) -> str:
        if blockers:
            return "blocked"

        if warnings:
            return "degraded"

        return "ready"
