from app.gaussian_import_validation import evaluate_imported_scene


def test_import_validation_rejects_bad_alignment_signature() -> None:
    result = evaluate_imported_scene(
        {"gaussian_count": 24000},
        {"observed_ratio": 0.62, "completion_candidate_ratio": 0.11},
        {"quality_gate": "warning"},
        {"gaussian_count": 1200},
        {"observed_ratio": 0.01, "completion_candidate_ratio": 0.92},
        {"quality_gate": "warning"},
        "splat",
        False,
    )

    assert result["validation_status"] == "reject"
    assert result["blockers"]


def test_import_validation_warns_when_scene_is_not_featured() -> None:
    result = evaluate_imported_scene(
        {"gaussian_count": 24000},
        {"observed_ratio": 0.62, "completion_candidate_ratio": 0.11},
        {"quality_gate": "warning"},
        {"gaussian_count": 20000},
        {"observed_ratio": 0.08, "completion_candidate_ratio": 0.22},
        {"quality_gate": "warning"},
        "splat",
        False,
    )

    assert result["validation_status"] == "warning"
    assert "featured-scene quality bar" in result["warnings"][0]


def test_import_validation_passes_supported_scene() -> None:
    result = evaluate_imported_scene(
        {"gaussian_count": 6465},
        {"observed_ratio": 0.0, "completion_candidate_ratio": 1.0},
        {"quality_gate": "warning"},
        {"gaussian_count": 24000},
        {"observed_ratio": 0.62, "completion_candidate_ratio": 0.11},
        {"quality_gate": "warning"},
        "splat",
        True,
    )

    assert result["validation_status"] == "pass"
    assert result["blockers"] == []
    assert result["warnings"] == []
