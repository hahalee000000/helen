"""Token 鉴权依赖的单元测试"""
import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient

from app.auth import require_auth, verify_ws_token
from app.config import settings


@pytest.fixture
def app_with_auth():
    """带鉴权的测试 app"""
    app = FastAPI()

    @app.get("/protected")
    async def protected(_token: str = Depends(require_auth)):
        return {"ok": True}

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket, token: str = verify_ws_token):
        await websocket.accept()
        await websocket.send_json({"authenticated": True})
        await websocket.close()

    return app


@pytest.fixture
def app_no_auth():
    """禁用鉴权的测试 app"""
    app = FastAPI()

    @app.get("/protected")
    async def protected(_token: str = Depends(require_auth)):
        return {"ok": True}

    return app


def test_auth_missing_token_returns_401(app_with_auth):
    settings.HELEN_WEBUI_TOKEN = "secret-token"
    try:
        client = TestClient(app_with_auth)
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "missing" in resp.json()["detail"].lower()
    finally:
        settings.HELEN_WEBUI_TOKEN = ""


def test_auth_wrong_token_returns_403(app_with_auth):
    settings.HELEN_WEBUI_TOKEN = "secret-token"
    try:
        client = TestClient(app_with_auth)
        resp = client.get("/protected", headers={"X-Helen-Token": "wrong"})
        assert resp.status_code == 403
    finally:
        settings.HELEN_WEBUI_TOKEN = ""


def test_auth_correct_token_returns_200(app_with_auth):
    settings.HELEN_WEBUI_TOKEN = "secret-token"
    try:
        client = TestClient(app_with_auth)
        resp = client.get("/protected", headers={"X-Helen-Token": "secret-token"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
    finally:
        settings.HELEN_WEBUI_TOKEN = ""


def test_auth_empty_token_disables_check(app_with_auth):
    settings.HELEN_WEBUI_TOKEN = ""
    client = TestClient(app_with_auth)
    # 无 header 也能通过（鉴权已禁用）
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_ws_missing_token_rejected(app_with_auth):
    settings.HELEN_WEBUI_TOKEN = "secret-token"
    try:
        client = TestClient(app_with_auth)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws"):
                pass
    finally:
        settings.HELEN_WEBUI_TOKEN = ""


def test_ws_correct_token_accepted(app_with_auth):
    settings.HELEN_WEBUI_TOKEN = "secret-token"
    try:
        client = TestClient(app_with_auth)
        with client.websocket_connect("/ws?token=secret-token") as ws:
            data = ws.receive_json()
            assert data == {"authenticated": True}
    finally:
        settings.HELEN_WEBUI_TOKEN = ""
