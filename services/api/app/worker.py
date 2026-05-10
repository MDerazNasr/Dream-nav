from time import sleep

from .jobs import JobRepository
from .processing_tasks import ProcessingTask, ProcessingTaskContext, default_processing_tasks

STEP_DELAY_SEC = 0.05
DEMO_OUTPUT_SCENE_ID = "warehouse_01"


class ProcessingWorker:
    def __init__(
        self,
        job_repository: JobRepository,
        tasks: list[ProcessingTask] | None = None,
        step_delay_sec: float = STEP_DELAY_SEC,
        output_scene_id: str = DEMO_OUTPUT_SCENE_ID,
    ) -> None:
        self.job_repository = job_repository
        self.tasks = tasks or default_processing_tasks()
        self.step_delay_sec = step_delay_sec
        self.output_scene_id = output_scene_id

    def process_next_job(self) -> str | None:
        job = self.job_repository.claim_next_queued_job()

        if not job:
            return None

        try:
            for task in self.tasks:
                self.job_repository.update_stage(job.job_id, task.step)
                result = task.run(
                    ProcessingTaskContext(
                        job=job,
                        upload_path=self.job_repository.upload_path(job),
                        artifacts_root=self.job_repository.artifact_root(job.job_id),
                    )
                )
                self.job_repository.write_artifact(job.job_id, result.artifact_name, result.payload)
                sleep(self.step_delay_sec)

            self.job_repository.complete_job(job.job_id, self.output_scene_id)
        except Exception as error:
            self.job_repository.fail_job(job.job_id, str(error))

        return job.job_id

    def process_available_jobs(self) -> list[str]:
        processed_job_ids = []

        while True:
            job_id = self.process_next_job()

            if not job_id:
                return processed_job_ids

            processed_job_ids.append(job_id)
