import pytest
from sanic import Sanic, response

from labfunctions import server
from labfunctions.conf.server_settings import settings
from labfunctions.db.nosync import AsyncSQL


def test_server_app():
    app = server.create_app(settings, ["events"])

    assert isinstance(app, Sanic)
    # assert isinstance(server.app.ctx.db, AsyncSQL)


def test_server_init_bp():
    app = Sanic("test_app_unique")
    server.init_blueprints(app, ["events", "workflows", "projects", "history"])
    assert len(app.blueprints) == 4


@pytest.mark.asyncio
async def test_server_status(sanic_app):
    req, res = await sanic_app.asgi_client.get("/status")

    assert res.status == 200
    assert res.json["msg"] == "We are ok"
