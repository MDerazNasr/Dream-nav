#!/usr/bin/env python3

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from sys import exit

try:
    from remote_dense_app.nerfstudio_diagnostics import NerfstudioDiagnosticsError, render_dataset_diagnostics
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from remote_dense_app.nerfstudio_diagnostics import NerfstudioDiagnosticsError, render_dataset_diagnostics


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Render comparable Nerfstudio training views for diagnostics.")
    parser.add_argument("--workspace-root", required=True, help="Path to nerfstudio-splatfacto-workspace.")
    parser.add_argument("--output-root", required=True, help="Path where diagnostic renders and contact sheet are written.")
    parser.add_argument("--render-command", default=None, help="Optional ns-render executable path.")
    parser.add_argument("--sample-count", type=int, default=6, help="How many training-view pairs to include in the contact sheet.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        manifest = render_dataset_diagnostics(
            workspace_root=Path(args.workspace_root),
            output_root=Path(args.output_root),
            render_command=args.render_command,
            sample_count=args.sample_count,
        )
    except NerfstudioDiagnosticsError as error:
        print(str(error))
        return 1

    print(manifest["summary_image"])
    return 0


if __name__ == "__main__":
    exit(main())
