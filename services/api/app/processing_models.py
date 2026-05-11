from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import ProcessingSettings
from .jobs import ProcessingStep, StoredJob


class ProcessingTaskFailed(Exception):
    def __init__(self, message: str, artifact_name: str | None = None) -> None:
        super().__init__(message)
        self.artifact_name = artifact_name


@dataclass(frozen=True)
class ProcessingTaskContext:
    job: StoredJob
    upload_path: Path
    artifacts_root: Path
    processing_settings: ProcessingSettings


@dataclass(frozen=True)
class ProcessingTaskResult:
    artifact_name: str
    payload: dict[str, object]


@dataclass(frozen=True)
class ProcessingCommand:
    artifact_name: str
    command: list[str]
    timeout_sec: float = 60


class ProcessingTaskRunner(Protocol):
    def __call__(self, context: ProcessingTaskContext) -> ProcessingTaskResult:
        pass


class ProcessingCommandBuilder(Protocol):
    def __call__(self, context: ProcessingTaskContext) -> ProcessingCommand | list[ProcessingCommand]:
        pass


@dataclass(frozen=True)
class ProcessingTask:
    step: ProcessingStep
    artifact_name: str
    run: ProcessingTaskRunner
    command_builder: ProcessingCommandBuilder | None = None
