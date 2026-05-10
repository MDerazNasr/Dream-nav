from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from subprocess import TimeoutExpired, run
from time import perf_counter
from typing import Sequence


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    cwd: str | None
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool

    def to_artifact(self) -> dict[str, object]:
        return asdict(self)


class CommandRunner:
    def run(
        self,
        command: Sequence[str],
        cwd: Path | None = None,
        timeout_sec: float = 60,
    ) -> CommandResult:
        if isinstance(command, str):
            raise TypeError("Command must be an argv sequence, not a shell string")

        command_args = list(command)
        if not command_args:
            raise ValueError("Command must not be empty")

        started_at = perf_counter()
        try:
            completed = run(
                command_args,
                capture_output=True,
                check=False,
                cwd=str(cwd) if cwd else None,
                text=True,
                timeout=timeout_sec,
            )
            return CommandResult(
                command=command_args,
                cwd=str(cwd) if cwd else None,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_ms=_duration_ms(started_at),
                timed_out=False,
            )
        except TimeoutExpired as error:
            return CommandResult(
                command=command_args,
                cwd=str(cwd) if cwd else None,
                exit_code=None,
                stdout=_decode_timeout_output(error.stdout),
                stderr=_decode_timeout_output(error.stderr),
                duration_ms=_duration_ms(started_at),
                timed_out=True,
            )


def _duration_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _decode_timeout_output(output: bytes | str | None) -> str:
    if output is None:
        return ""

    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")

    return output
