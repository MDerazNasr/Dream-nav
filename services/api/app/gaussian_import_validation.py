from __future__ import annotations

from typing import Any

REJECT_MIN_GAUSSIANS = 8000
REJECT_MIN_OBSERVED_RATIO = 0.02
REJECT_MAX_COMPLETION_RATIO = 0.85
WARNING_MIN_OBSERVED_RATIO = 0.05
WARNING_MAX_COMPLETION_RATIO = 0.6


def evaluate_imported_scene(
    previous_gaussian_scene: dict[str, Any] | None,
    previous_visibility: dict[str, Any] | None,
    previous_quality: dict[str, Any] | None,
    current_gaussian_scene: dict[str, Any],
    current_visibility: dict[str, Any],
    current_quality: dict[str, Any],
    viewer_render_mode: str,
    featured_candidate: bool,
) -> dict[str, object]:
    previous_gaussian_count = _int_value(previous_gaussian_scene, "gaussian_count")
    previous_observed_ratio = _float_value(previous_visibility, "observed_ratio")
    previous_completion_ratio = _float_value(previous_visibility, "completion_candidate_ratio")
    previous_quality_gate = _string_value(previous_quality, "quality_gate")
    current_gaussian_count = _int_value(current_gaussian_scene, "gaussian_count")
    current_observed_ratio = _float_value(current_visibility, "observed_ratio")
    current_completion_ratio = _float_value(current_visibility, "completion_candidate_ratio")
    current_quality_gate = _string_value(current_quality, "quality_gate")

    blockers: list[str] = []
    warnings: list[str] = []

    if viewer_render_mode != "splat":
        blockers.append("Imported scene did not produce a splat-ready viewer bundle.")

    if current_gaussian_count < REJECT_MIN_GAUSSIANS:
        blockers.append("Imported scene density is too low for a stable dense review.")

    if current_observed_ratio < REJECT_MIN_OBSERVED_RATIO:
        blockers.append("Observed coverage is too low, which strongly suggests a bad alignment.")

    if current_completion_ratio > REJECT_MAX_COMPLETION_RATIO:
        blockers.append("Completion coverage is too high, which suggests the imported scene is mostly unsupported.")

    if current_quality_gate == "fail":
        blockers.append("Quality gate is fail for the refreshed imported scene.")

    if (
        previous_observed_ratio is not None
        and current_observed_ratio < previous_observed_ratio * 0.4
        and current_completion_ratio > previous_completion_ratio_or_zero(previous_completion_ratio) + 0.2
    ):
        blockers.append("Observed coverage regressed sharply compared with the previous reconstruction.")

    if not blockers and current_observed_ratio < WARNING_MIN_OBSERVED_RATIO:
        warnings.append("Observed coverage is low, so the imported scene still needs manual review.")

    if not blockers and current_completion_ratio > WARNING_MAX_COMPLETION_RATIO:
        warnings.append("Completion-heavy coverage suggests the imported scene may still be misaligned.")

    if not blockers and not featured_candidate:
        warnings.append("Imported scene is still below the featured-scene quality bar.")

    validation_status = "reject" if blockers else "warning" if warnings else "pass"

    return {
        "previous_gaussian_count": previous_gaussian_count,
        "previous_observed_ratio": previous_observed_ratio,
        "previous_completion_candidate_ratio": previous_completion_ratio,
        "previous_quality_gate": previous_quality_gate,
        "observed_ratio": current_observed_ratio,
        "completion_candidate_ratio": current_completion_ratio,
        "quality_gate": current_quality_gate,
        "validation_status": validation_status,
        "blockers": blockers,
        "warnings": warnings,
    }


def _int_value(payload: dict[str, Any] | None, key: str) -> int | None:
    if not payload:
        return None
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _float_value(payload: dict[str, Any] | None, key: str) -> float:
    if not payload:
        return 0.0
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


def _string_value(payload: dict[str, Any] | None, key: str) -> str | None:
    if not payload:
        return None
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def previous_completion_ratio_or_zero(value: float | None) -> float:
    return value if isinstance(value, float) else 0.0
