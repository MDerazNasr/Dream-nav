from json import dumps
from pathlib import Path

import pytest

from app.quality_gate import QualityGateError, build_quality_gate_report, read_heldout_psnr


def test_quality_gate_passes_at_psnr_threshold() -> None:
    report = build_quality_gate_report(22)

    assert report["quality_gate"] == "pass"
    assert report["completion_policy"] == "enabled"
    assert report["pass_threshold_psnr"] == 22


def test_quality_gate_warns_below_pass_threshold() -> None:
    report = build_quality_gate_report(21.4)

    assert report["quality_gate"] == "warning"
    assert report["completion_policy"] == "warning_overlay"
    assert "below 22 dB" in str(report["quality_gate_reason"])


def test_quality_gate_fails_below_warning_threshold() -> None:
    report = build_quality_gate_report(19.9)

    assert report["quality_gate"] == "fail"
    assert report["completion_policy"] == "disabled"
    assert "below 20 dB" in str(report["quality_gate_reason"])


def test_quality_gate_fails_when_psnr_is_missing() -> None:
    report = build_quality_gate_report(None)

    assert report["quality_gate"] == "fail"
    assert report["completion_policy"] == "disabled"


def test_quality_gate_reads_heldout_psnr(tmp_path: Path) -> None:
    (tmp_path / "heldout_evaluation.json").write_text(
        dumps({"heldout_psnr_median": 23.2}),
        encoding="utf-8",
    )

    assert read_heldout_psnr(tmp_path) == 23.2


def test_quality_gate_fails_invalid_evaluation_artifact(tmp_path: Path) -> None:
    (tmp_path / "heldout_evaluation.json").write_text("[]", encoding="utf-8")

    with pytest.raises(QualityGateError, match="must be a JSON object"):
        read_heldout_psnr(tmp_path)
