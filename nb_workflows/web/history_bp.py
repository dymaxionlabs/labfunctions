# pylint: disable=unused-argument
import json as std_json
import pathlib
from dataclasses import asdict

from sanic import Blueprint
from sanic.response import json
from sanic_ext import openapi
from sanic_jwt import inject_user, protected

from nb_workflows.conf import defaults
from nb_workflows.conf.server_settings import settings
from nb_workflows.core.registers import register_history_db
from nb_workflows.io import AsyncFileserver
from nb_workflows.managers import history_mg
from nb_workflows.types import ExecutionResult, HistoryRequest, NBTask
from nb_workflows.utils import get_query_param, today_string

history_bp = Blueprint("history", url_prefix="history")

# async def validate_project(request):
#     request.ctx.user = await extract_user_from_request(request)


@history_bp.get("/<jobid>")
@openapi.parameter("jobid", str, "path")
@openapi.response(200, "Found")
@openapi.response(404, dict(msg=str), "Not Found")
@openapi.parameter("lt", int, "lt")
@protected()
async def history_last_job(request, jobid):
    """Get the status of the last job executed"""
    # pylint: disable=unused-argument
    lt = get_query_param(request, "lt", 1)
    session = request.ctx.session
    async with session.begin():
        h = await history_mg.get_last(session, jobid, limit=lt)
        if h:
            return json(asdict(h), 200)

        return json(dict(msg="not found"), 404)


@history_bp.post("/")
@openapi.body({"application/json": HistoryRequest})
@openapi.response(201, "Created")
@protected()
async def history_create(request):
    """Register a jobexecution"""
    # pylint: disable=unused-argument

    dict_ = request.json
    # task = NBTask(**dict_["task"])
    result = ExecutionResult(**dict_)
    session = request.ctx.session
    async with session.begin():
        hm = await history_mg.create(session, result)

    return json(dict(msg="created"), 201)


@history_bp.get("/test")
# @openapi.parameter("projectid", str, "path")
# @openapi.parameter("jobid", str, "path")
@inject_user()
@protected()
async def project_test(request, user):
    """
    Upload a workflow project
    """
    breakpoint()
    print(user)

    return json(dict(msg="OK"), 201)


@history_bp.post("/<projectid>/_output_ok")
@openapi.parameter("projectid", str, "path")
@protected()
async def history_output_ok(request, projectid):
    """
    Upload a workflow project
    """
    # pylint: disable=unused-argument
    fsrv = AsyncFileserver(settings.FILESERVER)
    today = today_string(format_="day")
    root = pathlib.Path(projectid)
    output_dir = root / defaults.NB_OUTPUTS / "ok" / today

    file_body = request.files["file"][0].body
    output_name = request.form["output_name"][0]

    fp = str(root / output_name)
    await fsrv.put(fp, file_body)

    return json(dict(msg="OK"), 201)


@history_bp.post("/<projectid>/_output_fail")
@openapi.parameter("projectid", str, "path")
@openapi.parameter("projectid", str, "path")
@protected()
async def history_output_fail(request, projectid):
    """
    Upload a workflow project
    """
    # pylint: disable=unused-argument

    fsrv = AsyncFileserver(settings.FILESERVER)
    today = today_string(format_="day")
    root = pathlib.Path(projectid / defaults.NB_OUTPUTS / "fail" / today)

    file_body = request.files["file"][0].body
    output_name = request.form["output_name"][0]

    fp = str(root / output_name)
    await fsrv.put(fp, file_body)

    return json(dict(msg="OK"), 201)