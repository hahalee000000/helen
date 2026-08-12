"""Tests for app.main — FastAPI app factory, lifespan, and endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, lifespan


# ── Lifespan ────────────────────────────────────────────────────────────────

class TestLifespan:
    def test_lifespan_initializes_websocket_manager(self):
        """After lifespan startup, app.state.websocket_manager should exist."""
        client = TestClient(app)
        with client:
            assert hasattr(app.state, "websocket_manager")
            assert app.state.websocket_manager is not None

    def test_lifespan_websocket_manager_has_active_connections(self):
        """WebSocketManager should have an active_connections list."""
        client = TestClient(app)
        with client:
            manager = app.state.websocket_manager
            assert hasattr(manager, "active_connections")
            assert isinstance(manager.active_connections, list)


# ── Root endpoint ───────────────────────────────────────────────────────────

class TestRootEndpoint:
    def test_root_returns_200(self):
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_returns_api_info(self):
        client = TestClient(app)
        resp = client.get("/")
        data = resp.json()
        assert "message" in data
        assert data["message"] == "Helen Web UI API"

    def test_root_returns_version(self):
        client = TestClient(app)
        resp = client.get("/")
        data = resp.json()
        assert "version" in data
        assert data["version"] == settings.VERSION

    def test_root_returns_docs_url(self):
        client = TestClient(app)
        resp = client.get("/")
        data = resp.json()
        assert "docs" in data
        assert data["docs"] == "/docs"


# ── Health endpoint ─────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self):
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_status_ok(self):
        client = TestClient(app)
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_returns_app_name(self):
        client = TestClient(app)
        resp = client.get("/health")
        data = resp.json()
        assert "app" in data
        assert data["app"] == settings.APP_NAME

    def test_health_no_auth_required(self):
        """Health endpoint should work without token (no auth dependency)."""
        # Even with auth disabled by fixture, health should always work
        settings.HELEN_WEBUI_TOKEN = ""
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200


# ── API status endpoint ─────────────────────────────────────────────────────

class TestApiStatusEndpoint:
    def test_api_status_returns_200(self):
        client = TestClient(app)
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_api_status_returns_version(self):
        client = TestClient(app)
        resp = client.get("/api/status")
        data = resp.json()
        assert "version" in data
        assert data["version"] == settings.VERSION

    def test_api_status_returns_active_connections(self):
        client = TestClient(app)
        resp = client.get("/api/status")
        data = resp.json()
        assert "active_connections" in data
        assert isinstance(data["active_connections"], int)

    def test_api_status_returns_config(self):
        client = TestClient(app)
        resp = client.get("/api/status")
        data = resp.json()
        assert "config" in data
        assert "helen_path" in data["config"]

    def test_api_status_returns_ok_status(self):
        client = TestClient(app)
        resp = client.get("/api/status")
        data = resp.json()
        assert data["status"] == "ok"


# ── Router registration ─────────────────────────────────────────────────────

class TestRouterRegistration:
    def test_chat_routes_registered(self):
        """Chat routes should be mounted under /api/chat prefix."""
        routes = [route.path for route in app.routes]
        chat_routes = [r for r in routes if r.startswith("/api/chat")]
        assert len(chat_routes) > 0

    def test_agents_routes_registered(self):
        """Agents routes should be mounted under /api/agents prefix."""
        routes = [route.path for route in app.routes]
        agents_routes = [r for r in routes if r.startswith("/api/agents")]
        assert len(agents_routes) > 0

    def test_root_route_registered(self):
        routes = [route.path for route in app.routes]
        assert "/" in routes

    def test_health_route_registered(self):
        routes = [route.path for route in app.routes]
        assert "/health" in routes

    def test_api_status_route_registered(self):
        routes = [route.path for route in app.routes]
        assert "/api/status" in routes


# ── App metadata ────────────────────────────────────────────────────────────

class TestAppMetadata:
    def test_app_title(self):
        assert app.title == settings.APP_NAME

    def test_app_version(self):
        assert app.version == settings.VERSION

    def test_app_description(self):
        assert "Helen" in app.description
