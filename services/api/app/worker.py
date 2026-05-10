from time import sleep

from .command_runner import CommandRunner
from .config import ProcessingSettings
from .jobs import JobRepository
from .processing_tasks import (
    ProcessingCommand,
    ProcessingTask,
    ProcessingTaskContext,
    ProcessingTaskFailed,
    default_processing_tasks,
)

STEP_DELAY_SEC = 0.05
DEMO_OUTPUT_SCENE_ID = "warehouse_01"


class ProcessingWorker:
    def __init__(
        self,
        job_repository: JobRepository,
        tasks: list[ProcessingTask] | None = None,
        command_runner: CommandRunner | None = None,
        processing_settings: ProcessingSettings | None = None,
        step_delay_sec: float = STEP_DELAY_SEC,
        output_scene_id: str = DEMO_OUTPUT_SCENE_ID,
    ) -> None:
        self.job_repository = job_repository
        self.tasks = tasks or default_processing_tasks()
        self.command_runner = command_runner or CommandRunner()
        self.processing_settings = processing_settings or ProcessingSettings()
        self.step_delay_sec = step_delay_sec
        self.output_scene_id = output_scene_id

    def process_next_job(self) -> str | None:
        job = self.job_repository.claim_next_queued_job()

        if not job:
            return None

        try:
            for task in self.tasks:
                self.job_repository.update_stage(job.job_id, task.step)
                context = ProcessingTaskContext(
                    job=job,
                    upload_path=self.job_repository.upload_path(job),
                    artifacts_root=self.job_repository.artifact_root(job.job_id),
                    processing_settings=self.processing_settings,
                )

                if task.command_builder:
                    self._run_task_command(job.job_id, task.command_builder(context))

                result = task.run(context)
                self.job_repository.write_artifact(job.job_id, result.artifact_name, result.payload)
                sleep(self.step_delay_sec)

            self.job_repository.complete_job(job.job_id, self.output_scene_id)
        except Exception as error:
            self.job_repository.fail_job(job.job_id, str(error))

        return job.job_id

    def _run_task_command(self, job_id: str, command: ProcessingCommand) -> None:
        artifact_root = self.job_repository.artifact_root(job_id)
        artifact_root.mkdir(parents=True, exist_ok=True)
        result = self.command_runner.run(
            command.command,
            cwd=artifact_root,
            timeout_sec=command.timeout_sec,
        )
        self.job_repository.write_artifact(job_id, command.artifact_name, result.to_artifact())

        if result.timed_out:
            raise ProcessingTaskFailed(f"Command timed out: {command.command[0]}")

        if result.exit_code != 0:
            raise ProcessingTaskFailed(f"Command failed with exit code {result.exit_code}: {command.command[0]}")

    def process_available_jobs(self) -> list[str]:
        processed_job_ids = []

        while True:
            job_id = self.process_next_job()

            if not job_id:
                return processed_job_ids

            processed_job_ids.append(job_id)
