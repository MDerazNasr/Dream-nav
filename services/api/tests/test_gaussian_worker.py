from pathlib import Path
from io import BytesIO
from json import loads

import anyio
from fastapi import UploadFile

from app.config import ProcessingSettings
from app.jobs import JobRepository
from app.worker import ProcessingWorker


def test_worker_runs_configured_gaussian_command(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    fake_gaussian = tmp_path / "fake_gaussian.py"
    fake_gaussian.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "from struct import pack\n"
        "import sys\n"
        "output = Path(sys.argv[sys.argv.index('--output-splat') + 1])\n"
        "properties = ['x', 'y', 'z', 'f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity', 'scale_0', 'scale_1', 'scale_2', 'rot_0', 'rot_1', 'rot_2', 'rot_3']\n"
        "header = '\\n'.join(['ply', 'format binary_little_endian 1.0', 'element vertex 4', *(f'property float {name}' for name in properties), 'end_header\\n'])\n"
        "rows = b''.join(pack('<14f', index * 0.2, 1.2, -index * 0.3, 1, 0, 0, 4, -1, -1, -1, 0, 0, 0, 1) for index in range(4))\n"
        "output.write_bytes(header.encode('utf-8') + rows)\n"
        "print('fake gaussian ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_gaussian.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            gaussian_backend="command",
            gaussian_command=str(fake_gaussian),
            gaussian_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)
    command_artifact = _read_job_artifact(tmp_path, response.job_id, "gaussian_scene_command.json")
    gaussian_scene = _read_job_artifact(tmp_path, response.job_id, "gaussian_scene.json")

    assert status.state == "completed"
    assert command_artifact["command"][0] == str(fake_gaussian)
    assert "--output-splat" in command_artifact["command"]
    assert "--colmap-command" not in command_artifact["command"]
    assert gaussian_scene["backend"] == "command"
    assert gaussian_scene["command_mode"] == "external"
    assert gaussian_scene["gaussian_count"] == 4
    assert gaussian_scene["splat_source"] == "existing"


def test_worker_fails_when_gaussian_command_is_missing(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            gaussian_backend="command",
            gaussian_command=str(tmp_path / "missing_gaussian"),
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.failed_stage == "building_gaussian_scene"
    assert status.error_message == "Gaussian backend command selected but DREAMNAV_GAUSSIAN_COMMAND was not found."


def test_worker_fails_when_gaussian_command_skips_splat(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    fake_gaussian = tmp_path / "fake_gaussian_no_output.py"
    fake_gaussian.write_text(
        "#!/usr/bin/env python3\n"
        "print('no splat written')\n",
        encoding="utf-8",
    )
    fake_gaussian.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            gaussian_backend="command",
            gaussian_command=str(fake_gaussian),
            gaussian_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)

    assert status.state == "failed"
    assert status.failed_stage == "building_gaussian_scene"
    assert status.error_message == "Gaussian reconstruction did not produce splat.ply."


def test_worker_builds_splat_from_colmap_sparse_points(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "if sys.argv[1] == 'mapper':\n"
        "    sparse = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    (sparse / '0').mkdir(parents=True, exist_ok=True)\n"
        "if sys.argv[1] == 'model_converter':\n"
        "    output = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    output.mkdir(parents=True, exist_ok=True)\n"
        "    (output / 'cameras.txt').write_text('1 PINHOLE 1920 1080 1200 1210 960 540\\n')\n"
        "    (output / 'images.txt').write_text(\n"
        "        '1 1 0 0 0 0 0 0 1 frame_0000.jpg\\n\\n'\n"
        "        '2 1 0 0 0 -1 -2 -3 1 frame_0001.jpg\\n\\n'\n"
        "        '3 1 0 0 0 -2 -4 -6 1 frame_0002.jpg\\n\\n'\n"
        "    )\n"
        "    (output / 'points3D.txt').write_text(\n"
        "        '1 0.0 1.0 -2.0 255 0 0 0.5 1 1 2\\n'\n"
        "        '2 0.5 1.2 -2.4 0 255 128 1.0 1 2 2\\n'\n"
        "    )\n"
        "print('fake colmap ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_colmap.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            pose_backend="colmap",
            pose_command=str(fake_colmap),
            gaussian_backend="command",
            gaussian_command=str(Path(__file__).parents[1] / "app" / "colmap_sparse_to_splat.py"),
            pose_timeout_sec=5,
            gaussian_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)
    gaussian_scene = _read_job_artifact(tmp_path, response.job_id, "gaussian_scene.json")

    assert status.state == "completed"
    assert gaussian_scene["backend"] == "command"
    assert gaussian_scene["gaussian_count"] == 2
    assert gaussian_scene["splat_source"] == "existing"


def test_worker_builds_splat_from_colmap_dense_points(tmp_path: Path) -> None:
    repo = _job_repository(tmp_path)
    fake_colmap = tmp_path / "fake_colmap.py"
    fake_colmap.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "command = sys.argv[1]\n"
        "if command == 'mapper':\n"
        "    sparse = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    (sparse / '0').mkdir(parents=True, exist_ok=True)\n"
        "if command == 'model_converter':\n"
        "    output = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    output.mkdir(parents=True, exist_ok=True)\n"
        "    (output / 'cameras.txt').write_text('1 SIMPLE_RADIAL 1920 1080 1200 960 540 0.01\\n')\n"
        "    (output / 'images.txt').write_text(\n"
        "        '1 1 0 0 0 0 0 0 1 frame_0000.jpg\\n\\n'\n"
        "        '2 1 0 0 0 -1 -2 -3 1 frame_0001.jpg\\n\\n'\n"
        "        '3 1 0 0 0 -2 -4 -6 1 frame_0002.jpg\\n\\n'\n"
        "    )\n"
        "    (output / 'points3D.txt').write_text('1 0.0 1.0 -2.0 255 0 0 0.5 1 1 2\\n')\n"
        "if command == 'image_undistorter':\n"
        "    output = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    output.mkdir(parents=True, exist_ok=True)\n"
        "if command == 'patch_match_stereo':\n"
        "    workspace = Path(sys.argv[sys.argv.index('--workspace_path') + 1])\n"
        "    workspace.mkdir(parents=True, exist_ok=True)\n"
        "if command == 'stereo_fusion':\n"
        "    output = Path(sys.argv[sys.argv.index('--output_path') + 1])\n"
        "    output.parent.mkdir(parents=True, exist_ok=True)\n"
        "    output.write_text(\n"
        "        'ply\\n'\n"
        "        'format ascii 1.0\\n'\n"
        "        'element vertex 3\\n'\n"
        "        'property float x\\n'\n"
        "        'property float y\\n'\n"
        "        'property float z\\n'\n"
        "        'property uchar red\\n'\n"
        "        'property uchar green\\n'\n"
        "        'property uchar blue\\n'\n"
        "        'end_header\\n'\n"
        "        '0 1 -2 255 0 0\\n'\n"
        "        '0.4 1.1 -2.2 0 255 64\\n'\n"
        "        '0.8 1.3 -2.6 0 32 255\\n',\n"
        "        encoding='utf-8',\n"
        "    )\n"
        "print('fake colmap ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_colmap.chmod(0o755)
    response = anyio.run(
        repo.create_upload_job,
        UploadFile(filename="walkthrough.mp4", file=BytesIO(b"video-bytes")),
    )
    worker = ProcessingWorker(
        repo,
        processing_settings=ProcessingSettings(
            pose_backend="colmap",
            pose_command=str(fake_colmap),
            gaussian_backend="command",
            gaussian_command=str(Path(__file__).parents[1] / "app" / "colmap_dense_to_splat.py"),
            pose_timeout_sec=5,
            gaussian_timeout_sec=5,
        ),
        step_delay_sec=0,
    )

    worker.process_next_job()
    status = repo.get_status(response.job_id)
    command_artifact = _read_job_artifact(tmp_path, response.job_id, "gaussian_scene_command.json")
    gaussian_scene = _read_job_artifact(tmp_path, response.job_id, "gaussian_scene.json")

    assert status.state == "completed"
    assert command_artifact["command"][0].endswith("colmap_dense_to_splat.py")
    assert "--colmap-command" in command_artifact["command"]
    assert str(fake_colmap) in command_artifact["command"]
    assert gaussian_scene["backend"] == "command"
    assert gaussian_scene["gaussian_count"] == 3
    assert gaussian_scene["splat_source"] == "existing"


def _job_repository(tmp_path: Path) -> JobRepository:
    return JobRepository(
        jobs_root=tmp_path / "data" / "jobs",
        uploads_root=tmp_path / "data" / "uploads",
    )


def _read_job_artifact(tmp_path: Path, job_id: str, artifact_name: str) -> dict[str, object]:
    artifact_path = tmp_path / "data" / "jobs" / job_id / "artifacts" / artifact_name
    return loads(artifact_path.read_text(encoding="utf-8"))
