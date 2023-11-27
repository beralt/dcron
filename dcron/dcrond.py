import docker
import docker.models.containers
import logging
import croniter
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import time

client = docker.from_env()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
)
logger = logging.getLogger("dcrond")
logger.setLevel(logging.INFO)


class Job:
    def __init__(self, container: docker.models.containers.Container, name: str):
        self._container = container
        self._name = name
        self._itr: Optional[croniter.croniter] = None
        self._cmd: Optional[str] = None
        self._deadline = datetime.now()
        self._parse()

    def _parse(self):
        for key, value in self._container.labels.items():
            if key.startswith(f"dcron.jobs.{self._name}"):
                parts = key.split(".")
                if parts[3] == "rule":
                    self._itr = croniter.croniter(value, datetime.now())
                    self._deadline = self._itr.get_next(datetime)
                    assert self._deadline > datetime.now()
                if parts[3] == "execute" or parts[3] == "run":
                    self._cmd = value

    @property
    def deadline(self) -> datetime:
        return self._deadline

    def run(self) -> None:
        code, result = self._container.exec_run(cmd=self._cmd)
        # stream result
        logger.info(result.decode("utf-8"))
        self._deadline = self._itr.get_next(datetime)


def get_container_id() -> Optional[str]:
    with open("/proc/self/mountinfo", "r") as file:
        line = file.readline().strip()
        while line:
            if "/docker/containers/" in line:
                container_id = line.split("/docker/containers/")[-1]
                return container_id.split("/")[0]
            line = file.readline().strip()
    return None


def get_compose_project() -> Optional[str]:
    self_container_id = get_container_id()
    if self_container_id:
        logger.info(f"running as container {self_container_id}")
        self_container = client.containers.get(self_container_id)
        # find the compose label
        for k, v in self_container.labels.items():
            if k == "com.docker.compose.project":
                return v
    return None


def get_jobs() -> Dict[str, Job]:
    compose_project = get_compose_project()
    if compose_project:
        logger.info(f"using compose project {compose_project}")
        containers = client.containers.list(
            filters={"label": f"com.docker.compose.project={compose_project}"}
        )
    else:
        logger.info(f"unable to detect compose project")
        # just loop over every single container we can find
        containers = client.containers.list()
    jobs = {}
    for c in containers:
        for key, value in c.labels.items():
            if key.startswith("dcron.jobs."):
                parts = key.split(".")
                if len(parts) < 4:
                    logger.warning(f"Unable to parse dcron jobs label: {key}={value}")
                    continue
                name = parts[2]
                if not name in jobs:
                    logger.info(f"adding job {name} for container {c.name}")
                    jobs[name] = Job(c, name=parts[2])
    return jobs


def cli():
    jobs = get_jobs()
    while len(jobs) == 0:
        logger.warning(f"no jobs found")
        time.sleep(10)
        jobs = get_jobs()
    while True:
        now = datetime.now()
        # run pending jobs
        next_deadline: Optional[datetime] = None
        next_job: Optional[str] = None
        for name, job in jobs.items():
            if job.deadline < now:
                logger.info(f"running job '{name}' with deadline {job.deadline}")
                job.run()
            if next_deadline is None or job.deadline < next_deadline:
                next_deadline = job.deadline
                next_job = name
        seconds = max(1, (next_deadline - now).seconds)
        logger.info(
            f"next job {next_job} deadline is at {next_deadline}, sleeping for {seconds} seconds"
        )
        time.sleep(seconds)


if __name__ == "__main__":
    cli()
