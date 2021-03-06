import shutil
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from labfunctions.client.nbclient import NBClient
from labfunctions.conf.server_settings import settings
from labfunctions.io.kvspec import GenericKVSpec
from labfunctions.runtimes import builder

from .factories import BuildCtxFactory, DockerBuildLogFactory, ProjectDataFactory

# spy = mocker.spy(builder, "docker_build")


@pytest.fixture
def kvstore() -> GenericKVSpec:
    kv = GenericKVSpec.create("labfunctions.io.kv_local.KVLocal", "labfunctions")
    return kv


def test_builder_unzip_runtime(mocker: MockerFixture, tempdir):
    settings.BASE_PATH = tempdir
    shutil.make_archive(
        f"{tempdir}/testzip", format="zip", root_dir="labfunctions/runtimes"
    )
    builder.unzip_runtime(f"{tempdir}/testzip.zip", tempdir)

    is_file = Path(f"{tempdir}/__init__.py").is_file()

    assert is_file


def test_builder_BuildTask_init(mocker: MockerFixture, kvstore):
    client = NBClient(url_service="http://localhost:8000")
    task = builder.BuildTask(client, kvstore=kvstore)

    assert isinstance(task.client, NBClient)


def test_builder_BuildTask_get_runtime(mocker: MockerFixture, kvstore, tempdir):
    def stream_data(any_):
        for x in range(5):
            yield str(x).encode()

    mock = mocker.MagicMock()
    mock.get_stream.return_value = [str(x).encode() for x in range(6)]
    # mock.get_stream = stream_data
    client = NBClient(url_service="http://localhost:8000")
    task = builder.BuildTask(client, kvstore=kvstore)
    task.kv = mock
    task.get_runtime_file(f"{tempdir}/test.zip", "dowload_zip_url")
    is_file = Path(f"{tempdir}/test.zip").is_file()
    assert is_file
    assert mock.get_stream.called


def test_builder_BuildTask_run(mocker: MockerFixture, kvstore, tempdir):

    client = NBClient(url_service="http://localhost:8000")
    ctx = BuildCtxFactory()

    log = DockerBuildLogFactory(error=True)
    unzip = mocker.patch(
        "labfunctions.runtimes.builder.unzip_runtime", return_value=None
    )
    get_runtime = mocker.patch(
        "labfunctions.runtimes.builder.BuildTask.get_runtime_file", return_value=None
    )
    cmd = mocker.patch(
        "labfunctions.runtimes.builder.DockerCommand.build", return_value=log
    )

    task = builder.BuildTask(client, kvstore=kvstore)
    log_run = task.run(ctx)
    assert unzip.called
    assert get_runtime.called
    assert cmd.called
    assert log_run.error
    assert cmd.call_args_list[0][1]["tag"] == "nbworkflows/test"


def test_builder_BuildTask_run_repo(mocker: MockerFixture, kvstore, tempdir):

    client = NBClient(url_service="http://localhost:8000")
    ctx = BuildCtxFactory(registry="testregistry")

    log = DockerBuildLogFactory(error=True)
    unzip = mocker.patch(
        "labfunctions.runtimes.builder.unzip_runtime", return_value=None
    )
    get_runtime = mocker.patch(
        "labfunctions.runtimes.builder.BuildTask.get_runtime_file", return_value=None
    )
    cmd = mocker.patch(
        "labfunctions.runtimes.builder.DockerCommand.build", return_value=log
    )

    task = builder.BuildTask(client, kvstore=kvstore)
    log_run = task.run(ctx)
    assert unzip.called
    assert get_runtime.called
    assert cmd.called
    assert log_run.error
    assert cmd.call_args_list[0][1]["tag"] == "testregistry/nbworkflows/test"


def test_builder_exec(mocker: MockerFixture, kvstore):
    agent_mock = mocker.MagicMock()
    build_mock = mocker.MagicMock()

    ctx = BuildCtxFactory()
    log = DockerBuildLogFactory()
    # spy = mocker.spy(builder, "BuildTask")
    # task_mock = mocker.patch(
    #    "labfunctions.runtimes.builder.BuildTask", return_value=build_mock
    # )
    task_mock = mocker.patch(
        "labfunctions.runtimes.builder.BuildTask.run", return_value=log
    )
    agent = mocker.patch(
        "labfunctions.runtimes.builder.client.from_env", return_value=agent_mock
    )
    task_mock.run.return_value = mocker.Mock(return_value=log)

    result = builder.builder_exec(ctx)

    assert id(result) == id(log)
    assert task_mock.call_args[0][0].execid == ctx.execid
    # assert task_mock.call_args_list[0][0][0] == ctx.projectid
    assert result.error is False
