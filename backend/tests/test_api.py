import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password
from app.config import REPO_ROOT, Settings
from app.main import create_app

PASSWORD = "correct horse battery"


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "test.db"),
        secret_key="test-secret",
        admin_username="admin",
        admin_password_hash=hash_password(PASSWORD),
        cookie_secure=False,
        frontend_path=REPO_ROOT / "artifact" / "index.html",
    )
    return TestClient(create_app(settings))


@pytest.fixture
def authed(client):
    assert client.post("/api/login", json={"username": "admin", "password": PASSWORD}).status_code == 200
    return client


ENTRY = {"mediumId": "books", "date": "2026-11-03", "month": "2026-11", "title": "DDIA ch. 5", "depth": 3}


def test_login_rejects_wrong_password(client):
    assert client.post("/api/login", json={"username": "admin", "password": "nope"}).status_code == 401


def test_api_requires_login(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/entries").status_code == 401
    assert client.put("/api/entries/e1", json=ENTRY).status_code == 401


def test_login_me_logout(authed):
    assert authed.get("/api/me").json() == {"username": "admin", "role": "admin"}
    assert authed.post("/api/logout").status_code == 204
    assert authed.get("/api/me").status_code == 401


def test_default_mediums_seeded(authed):
    ids = [m["id"] for m in sorted(authed.get("/api/mediums").json(), key=lambda m: m["order"])]
    assert ids == ["books", "algorithms", "work-challenges", "tech-methods", "courses", "community"]


def test_entry_set_update_delete(authed):
    assert authed.put("/api/entries/e1", json=ENTRY).status_code == 204
    assert authed.patch("/api/entries/e1", json={"notes": "replication lag"}).status_code == 204
    [e] = authed.get("/api/entries").json()
    assert e == {**ENTRY, "id": "e1", "notes": "replication lag", "link": "", "createdAt": None, "updatedAt": None}
    assert authed.delete("/api/entries/e1").status_code == 204
    assert authed.get("/api/entries").json() == []


def test_update_missing_doc_is_404(authed):
    assert authed.patch("/api/entries/nope", json={"notes": "x"}).status_code == 404


def test_validation(authed):
    assert authed.put("/api/entries/e1", json={**ENTRY, "depth": 9}).status_code == 422
    assert authed.put("/api/entries/e1", json={**ENTRY, "month": "2026-10"}).status_code == 422
    assert authed.put("/api/entries/bad id", json=ENTRY).status_code == 422
    assert authed.put("/api/nothing/x", json={}).status_code == 404


def test_entry_needs_existing_medium(authed):
    assert authed.put("/api/entries/e1", json={**ENTRY, "mediumId": "ghost"}).status_code == 400


def test_month_and_medium_roundtrip(authed):
    snap = [{"id": "books", "name": "Books", "weight": 1, "archived": False}]
    assert authed.put("/api/months/2026-10", json={"score": 57, "mediums": snap, "finalizedAt": "t"}).status_code == 204
    assert authed.get("/api/months").json() == [{"id": "2026-10", "score": 57, "mediums": snap, "finalizedAt": "t"}]
    assert authed.patch("/api/mediums/books", json={"archived": True}).status_code == 204
    books = next(m for m in authed.get("/api/mediums").json() if m["id"] == "books")
    assert books["archived"] is True and books["name"] == "Books"


def test_import_shaped_payload_ignores_extra_fields(authed):
    # The artifact's JSON export rows carry "id" and possibly other fields; the client strips id.
    assert authed.put("/api/entries/e9", json={**ENTRY, "somethingElse": 1}).status_code == 204


def test_index_serves_wrapped_frontend(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.text.startswith("<!doctype html>") and "id=\"app\"" in r.text and r.text.endswith("</html>")


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}
