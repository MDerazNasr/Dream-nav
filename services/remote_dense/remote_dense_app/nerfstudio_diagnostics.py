from __future__ import annotations

from json import dumps
from pathlib import Path
from shutil import which
from subprocess import run


class NerfstudioDiagnosticsError(Exception):
    pass


def render_dataset_diagnostics(
    workspace_root: Path,
    output_root: Path,
    render_command: str | None = None,
    sample_count: int = 6,
) -> dict[str, object]:
    workspace_root = workspace_root.resolve(strict=True)
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    config_path = find_latest_config(workspace_root)
    resolved_render = resolve_render_command(render_command)
    render_output_root = output_root / "dataset-renders"

    command = [
        resolved_render,
        "dataset",
        "--load-config",
        str(config_path),
        "--split",
        "train",
        "--output-path",
        str(render_output_root),
        "--rendered-output-names",
        "gt-rgb",
        "rgb",
    ]
    completed = run(command, capture_output=True, check=False, text=True, cwd=str(workspace_root))
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "Nerfstudio dataset render failed."
        raise NerfstudioDiagnosticsError(details)

    pairs = collect_render_pairs(render_output_root)
    if not pairs:
        raise NerfstudioDiagnosticsError("Nerfstudio dataset render did not produce comparable gt-rgb and rgb images.")

    summary_path = write_contact_sheet(output_root, pairs, sample_count)
    manifest = {
        "config_path": str(config_path),
        "render_output_root": str(render_output_root),
        "pair_count": len(pairs),
        "sample_count": min(sample_count, len(pairs)),
        "summary_image": str(summary_path),
    }
    (output_root / "diagnostics_manifest.json").write_text(dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def find_latest_config(workspace_root: Path) -> Path:
    candidates = sorted(workspace_root.glob("outputs/**/config.yml"))
    if not candidates:
        raise NerfstudioDiagnosticsError("Nerfstudio workspace did not contain a training config.")
    return candidates[-1]


def resolve_render_command(render_command: str | None) -> str:
    configured = render_command or "ns-render"
    configured_path = Path(configured)
    if configured_path.parent != Path("."):
        if configured_path.is_file():
            return str(configured_path)
        raise NerfstudioDiagnosticsError("Configured Nerfstudio render command was not found.")

    resolved = which(configured)
    if resolved:
        return resolved
    raise NerfstudioDiagnosticsError("Nerfstudio render command was not found.")


def collect_render_pairs(render_output_root: Path) -> list[tuple[Path, Path, str]]:
    train_root = render_output_root / "train"
    rgb_root = train_root / "rgb"
    gt_root = train_root / "gt-rgb"
    if not rgb_root.is_dir() or not gt_root.is_dir():
        return []

    pairs: list[tuple[Path, Path, str]] = []
    for rgb_path in sorted(rgb_root.rglob("*.png")):
        relative_name = rgb_path.relative_to(rgb_root).with_suffix("")
        gt_path = gt_root / rgb_path.relative_to(rgb_root)
        if gt_path.is_file():
            pairs.append((gt_path, rgb_path, str(relative_name)))
    return pairs


def write_contact_sheet(
    output_root: Path,
    pairs: list[tuple[Path, Path, str]],
    sample_count: int,
) -> Path:
    try:
        from PIL import Image, ImageDraw
    except ModuleNotFoundError as error:
        raise NerfstudioDiagnosticsError("Pillow is required to write Nerfstudio diagnostic contact sheets.") from error

    selected_pairs = evenly_sample_pairs(pairs, sample_count)
    gt_images = [Image.open(gt_path).convert("RGB") for gt_path, _, _ in selected_pairs]
    rgb_images = [Image.open(rgb_path).convert("RGB") for _, rgb_path, _ in selected_pairs]
    labels = [label for _, _, label in selected_pairs]
    try:
        target_width = min(image.width for image in gt_images + rgb_images)
        target_height = min(image.height for image in gt_images + rgb_images)
        resized_gt = [image.resize((target_width, target_height)) for image in gt_images]
        resized_rgb = [image.resize((target_width, target_height)) for image in rgb_images]

        gutter = 20
        label_height = 28
        canvas = Image.new(
            "RGB",
            (target_width * 2 + gutter * 3, (target_height + label_height + gutter) * len(selected_pairs) + gutter),
            color=(17, 20, 18),
        )
        draw = ImageDraw.Draw(canvas)
        for index, (gt_image, rgb_image, label) in enumerate(zip(resized_gt, resized_rgb, labels, strict=True)):
            top = gutter + index * (target_height + label_height + gutter)
            draw.text((gutter, top), f"{label} · gt-rgb", fill=(223, 231, 223))
            draw.text((gutter * 2 + target_width, top), f"{label} · rgb", fill=(223, 231, 223))
            canvas.paste(gt_image, (gutter, top + label_height))
            canvas.paste(rgb_image, (gutter * 2 + target_width, top + label_height))

        summary_path = output_root / "training_view_contact_sheet.png"
        canvas.save(summary_path)
        return summary_path
    finally:
        for image in gt_images + rgb_images:
            image.close()


def evenly_sample_pairs(
    pairs: list[tuple[Path, Path, str]],
    sample_count: int,
) -> list[tuple[Path, Path, str]]:
    if sample_count <= 0 or sample_count >= len(pairs):
        return pairs
    if sample_count == 1:
        return [pairs[len(pairs) // 2]]

    step = (len(pairs) - 1) / (sample_count - 1)
    indices = []
    for index in range(sample_count):
        candidate = round(index * step)
        if candidate not in indices:
            indices.append(candidate)
    while len(indices) < sample_count:
        indices.append(indices[-1] + 1)
    return [pairs[index] for index in indices[:sample_count]]
