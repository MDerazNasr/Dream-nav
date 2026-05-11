from __future__ import annotations

from json import JSONDecodeError, loads
from math import isfinite
from pathlib import Path
from typing import Any

PASS_PSNR_THRESHOLD = 22.0
WARNING_PSNR_THRESHOLD = 20.0
QUALITY_GATE_VALUES = {"pass", "warning", "fail"}


class QualityGateError(Exception):
    pass


def read_heldout_psnr(artifacts_root: Path) -> float | None:
    try:
        payload = loads((artifacts_root / "heldout_evaluation.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, JSONDecodeError) as error:
        raise QualityGateError("Held-out evaluation artifact is missing or invalid.") from error

    if not isinstance(payload, dict):
        raise QualityGateError("Held-out evaluation artifact must be a JSON object.")

    return _optional_finite_number(payload.get("heldout_psnr_median"))


def build_quality_gate_report(heldout_psnr_median: float | None) -> dict[str, object]:
    psnr = _optional_finite_number(heldout_psnr_median)
    if psnr is None:
        return _report(
            "fail",
            psnr,
            "disabled",
            "Held-out PSNR is unavailable, so seamless completion is disabled.",
        )

    if psnr >= PASS_PSNR_THRESHOLD:
        return _report(
            "pass",
            psnr,
            "enabled",
            "Held-out PSNR meets the 22 dB pass threshold, so cached completion can be shown normally.",
        )

    if psnr >= WARNING_PSNR_THRESHOLD:
        return _report(
            "warning",
            psnr,
            "warning_overlay",
            "Held-out PSNR is below 22 dB but at least 20 dB, so completion stays labeled as lower confidence.",
        )

    return _report(
        "fail",
        psnr,
        "disabled",
        "Held-out PSNR is below 20 dB, so seamless completion is disabled.",
    )


def normalize_quality_gate_report(payload: dict[str, Any], heldout_psnr_median: float | None) -> dict[str, object]:
    quality_gate = payload.get("quality_gate")
    if isinstance(quality_gate, str) and quality_gate in QUALITY_GATE_VALUES:
        report = _report_for_status(quality_gate, heldout_psnr_median)
    else:
        report = build_quality_gate_report(heldout_psnr_median)

    reason = payload.get("quality_gate_reason")
    if isinstance(reason, str) and reason:
        report["quality_gate_reason"] = reason

    policy = payload.get("completion_policy")
    if policy in {"enabled", "warning_overlay", "disabled"}:
        report["completion_policy"] = policy

    return report


def _report_for_status(quality_gate: str, heldout_psnr_median: float | None) -> dict[str, object]:
    psnr = _optional_finite_number(heldout_psnr_median)
    if quality_gate == "pass":
        return _report("pass", psnr, "enabled", "Completion passed the configured PSNR quality gate.")
    if quality_gate == "warning":
        return _report("warning", psnr, "warning_overlay", "Completion requires warning labels under the PSNR gate.")
    return _report("fail", psnr, "disabled", "Completion failed the configured PSNR quality gate.")


def _report(
    quality_gate: str,
    heldout_psnr_median: float | None,
    completion_policy: str,
    quality_gate_reason: str,
) -> dict[str, object]:
    return {
        "heldout_psnr_median": heldout_psnr_median,
        "quality_gate": quality_gate,
        "completion_policy": completion_policy,
        "quality_gate_reason": quality_gate_reason,
        "warning_threshold_psnr": WARNING_PSNR_THRESHOLD,
        "pass_threshold_psnr": PASS_PSNR_THRESHOLD,
    }


def _optional_finite_number(value: object) -> float | None:
    if not isinstance(value, int | float):
        return None

    number = float(value)
    return number if isfinite(number) else None
