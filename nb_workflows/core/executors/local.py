from typing import Union

from nb_workflows import client
from nb_workflows.conf.client_settings import settings
from nb_workflows.core.entities import ExecutionResult, NBTask, ScheduleData
from nb_workflows.core.notebooks import nb_job_executor
from nb_workflows.utils import set_logger


def local_dev_exec(jobid) -> Union[ExecutionResult, None]:
    """Without server interaction
    jobid will be searched in the workflows file
    """
    logger = set_logger("local_exec", level=settings.LOGLEVEL)
    logger.info(f"Runing {jobid}")
    # nb_client = client.nb_from_file("workflows.yaml")

    wf = client.NBClient.read("workflows.yaml")
    for w in wf.workflows:
        if w.jobid == jobid:
            exec_res = nb_job_executor(w)
            # nb_client.register_history(exec_res, task)
            return exec_res
    print(f"{jobid} not found in workflows.yaml")
    return None


def local_exec(jobid) -> Union[ExecutionResult, None]:
    """It will run inside docker"""

    logger = set_logger("local_exec", level=settings.LOGLEVEL)
    logger.info(f"Runing {jobid}")
    # nb_client = client.nb_from_file("workflows.yaml", settings.WORKFLOW_SERVICE)
    nb_client = client.nb_from_settings_agent()
    try:
        rsp = nb_client.workflows_get(jobid)
        if rsp and rsp.enabled:
            task = NBTask(**rsp.job_detail)
            if task.schedule:
                task.schedule = ScheduleData(**rsp.job_detail["schedule"])
            exec_res = nb_job_executor(task)
            # nb_client.register_history(exec_res, task)
            return exec_res
        # elif not rsp:
        #    nb_client.rq_cancel_job(jobid)
        else:
            logger.warning(f"{jobid} not enabled")
    except KeyError:
        logger.error("Invalid credentials")
    except TypeError:
        logger.error("Something went wrong")
    return None
