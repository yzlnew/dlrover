# Copyright 2023 The DLRover Authors. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import sys
import time
from typing import List

import yaml
from ray.job_submission import JobSubmissionClient

_logger: logging.Logger = logging.getLogger(__name__)
_logger.setLevel("INFO")
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def split_lines(text: str) -> List[str]:
    lines = []
    while len(text) > 0:
        idx = text.find("\n")
        if idx >= 0:
            lines.append(text[: idx + 1])
            start = idx + 1
            text = text[start:]
        else:
            lines.append(text)
            break
    return lines


class RayJobSubimitter:
    """
    RayJobSubimiter is a dlrover interface to Ray.
    The job environment is specified by the TorchX workspace. Any files in
    the workspace will be present in the Ray job unless specified in
    **Config Options**
    .. runopts::
        class: torchx.schedulers.ray_scheduler.create_scheduler
    """

    def __init__(self, conf_path):
        self._conf_path = conf_path
        self.run_options = {}
        job_submission_addr = self.run_options["dashboardUrl"]
        self._dashboard_addr = job_submission_addr
        self._client = JobSubmissionClient(f"http://{job_submission_addr}")


    def _load_conf(self):
        with open(self._conf_path, "r", encoding="utf-8") as file:
            file_data = file.read()
            all_data = yaml.load_all(file_data, Loader=yaml.SafeLoader)
        self.run_options = all_data

    def submit(self):

        runtime_env = {"working_dir": self.run_options.get("workingDir", "./")}
        if self.run_options.get("requirements", None):
            runtime_env["pip"] = self.run_options.get("requirements")
        try:
            job_id: str = self._client.submit_job(
                entrypoint="python -c 'import time; time.sleep(10)'",
                runtime_env=runtime_env,
            )
        except Exception as e:
            _logger.error(e)
            _logger.error("fail to submit job")

        # Encode job submission client in job_id
        return f"{job_id}"

    def wait_until_finish(self, job_id: str, timeout: int = 30):
        """
        ``wait_until_finish`` waits until the specified job has finished
        with a given timeout. This is intended for testing. Programmatic
        usage should use the runner wait method instead.
        """
        start = time.time()
        while time.time() - start <= timeout:
            status_info = self._get_job_status(job_id)
            status = status_info
            if status in {"succeeded", "stopped", "failed"}:
                break
            time.sleep(1)

    def stop_job(self, job_id: str):  # pragma: no cover
        self._client.stop_job(job_id)

    def _get_job_status(self, job_id: str):
        status = self._client.get_job_status(job_id)
        print(status)
        return status

    def describe(self, job_id: str):
        pass

    def log_iter(
        self,
        job_id: str,
    ):
        logs: str = self._client.get_job_logs(job_id)
        iterator = split_lines(logs)
        return iterator

    def list(self):
        jobs = self._client.list_jobs()
        return jobs


def create_scheduler(conf_file_path=None):
    return RayJobSubimitter(conf_file_path)