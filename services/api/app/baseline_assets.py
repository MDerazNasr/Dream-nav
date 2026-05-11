from __future__ import annotations

from json import JSONDecodeError, loads
from pathlib import Path
from typing import Any


def build_nearest_view_baseline_svg(
    artifacts_root: Path,
    camera_path: dict[str, Any],
    nearest_pose_index: int | None,
) -> str:
    if nearest_pose_index is None:
        return fallback_nearest_view_svg(None)

    pseudo_view = _nearest_pseudo_view(artifacts_root, camera_path, nearest_pose_index)
    if pseudo_view is None:
        return fallback_nearest_view_svg(nearest_pose_index)

    rgb_path = pseudo_view.get("rgb_path")
    if not isinstance(rgb_path, str):
        return fallback_nearest_view_svg(nearest_pose_index)

    pixels = _read_ppm_pixels(artifacts_root / rgb_path)
    if pixels is None:
        return fallback_nearest_view_svg(nearest_pose_index)

    return _ppm_pixels_to_svg(pixels, nearest_pose_index)


def fallback_nearest_view_svg(nearest_pose_index: int | None) -> str:
    pose_label = "none" if nearest_pose_index is None else str(nearest_pose_index)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" role="img">
  <rect width="320" height="180" fill="#111412"/>
  <polygon points="0,0 320,0 263,80 58,77" fill="#38443d"/>
  <polygon points="0,180 58,77 263,80 320,180" fill="#202923"/>
  <polygon points="0,0 58,77 0,180" fill="#1b211e"/>
  <polygon points="320,0 263,80 320,180" fill="#171d1a"/>
  <path d="M70 125c43-8 88-12 171-4" fill="none" stroke="#b8c6bd" stroke-width="3" opacity="0.55"/>
  <rect x="112" y="38" width="64" height="44" fill="#56645c" opacity="0.42"/>
  <rect x="205" y="105" width="35" height="28" fill="#77857d" opacity="0.48"/>
  <text x="18" y="162" fill="#dfe7df" font-family="Arial, sans-serif" font-size="14">nearest view pose {pose_label}</text>
</svg>
"""


def _nearest_pseudo_view(
    artifacts_root: Path,
    camera_path: dict[str, Any],
    nearest_pose_index: int,
) -> dict[str, Any] | None:
    manifest = _read_json(artifacts_root / "pseudo_views.json")
    views = manifest.get("views") if manifest else None
    if not isinstance(views, list):
        return None

    source_pose_index = _source_pose_index(camera_path, nearest_pose_index)
    if source_pose_index is None:
        return None

    candidates = [
        view
        for view in views
        if isinstance(view, dict)
        and view.get("split") == "train"
        and view.get("source_pose_index") == source_pose_index
    ]
    if not candidates:
        return None

    return sorted(candidates, key=lambda view: str(view.get("view_id", "")))[0]


def _source_pose_index(camera_path: dict[str, Any], pose_index: int) -> int | None:
    poses = camera_path.get("poses")
    if not isinstance(poses, list) or pose_index >= len(poses):
        return None

    pose = poses[pose_index]
    if not isinstance(pose, dict):
        return None

    frame_index = pose.get("frame_index")
    return int(frame_index) if isinstance(frame_index, int | float) else pose_index


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _read_ppm_pixels(path: Path) -> tuple[int, int, list[tuple[int, int, int]]] | None:
    try:
        tokens = path.read_text(encoding="ascii").split()
    except FileNotFoundError:
        return None

    if len(tokens) < 4 or tokens[0] != "P3":
        return None

    width = _int_token(tokens[1])
    height = _int_token(tokens[2])
    max_value = _int_token(tokens[3])
    if width is None or height is None or max_value is None or width <= 0 or height <= 0 or max_value <= 0:
        return None

    values = [_int_token(token) for token in tokens[4:]]
    if any(value is None for value in values) or len(values) < width * height * 3:
        return None

    scale = 255 / max_value
    pixels = []
    for index in range(0, width * height * 3, 3):
        r = round(values[index] * scale)
        g = round(values[index + 1] * scale)
        b = round(values[index + 2] * scale)
        pixels.append((r, g, b))

    return width, height, pixels


def _ppm_pixels_to_svg(pixels: tuple[int, int, list[tuple[int, int, int]]], nearest_pose_index: int) -> str:
    width, height, colors = pixels
    cell_width = 320 / width
    cell_height = 180 / height
    rects = []
    for index, color in enumerate(colors):
        x = (index % width) * cell_width
        y = (index // width) * cell_height
        rects.append(
            f'  <rect x="{x:.2f}" y="{y:.2f}" width="{cell_width:.2f}" height="{cell_height:.2f}" '
            f'fill="rgb({color[0]},{color[1]},{color[2]})"/>'
        )

    label = (
        '  <text x="18" y="162" fill="#111412" font-family="Arial, sans-serif" '
        f'font-size="14">pseudo-view pose {nearest_pose_index}</text>'
    )
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" role="img">',
            *rects,
            label,
            "</svg>",
            "",
        ]
    )


def _int_token(token: str) -> int | None:
    try:
        return int(token)
    except ValueError:
        return None
