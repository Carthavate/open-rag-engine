import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from open_rag_engine.api import create_app
from open_rag_engine.library import Library

from .conftest import FakeModels, HashEmbeddings, OverlapCrossEncoder
from .test_library import ManualExecutor, write

TOKEN = "t" * 32
ORIGIN = "https://app.ore"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def make_client(library: Library, base_url: str = "http://127.0.0.1:8765") -> TestClient:
    return TestClient(create_app(library, token=TOKEN, origins=[ORIGIN]), base_url=base_url)


@pytest.fixture
def library(config) -> Library:
    return Library(
        config, FakeModels(HashEmbeddings(), OverlapCrossEncoder(), FakeListChatModel(responses=["1.2 kW [1]."]))
    )


@pytest.fixture
def client(library) -> TestClient:
    return make_client(library)


def test_every_request_needs_the_token(client: TestClient):
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = client.get("/health", headers=AUTH)
    assert response.status_code == 200 and response.json()["status"] == "ok"


def test_only_loopback_hosts_are_served(library: Library):
    assert make_client(library, "http://evil.example").get("/health", headers=AUTH).status_code == 400


def test_cors_allows_only_the_app_origin(client: TestClient):
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization"}
    ok = client.options("/ask", headers={"Origin": ORIGIN, **preflight})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == ORIGIN
    denied = client.options("/ask", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in denied.headers


def create_section(client: TestClient, folder: Path) -> str:
    category = client.post("/categories", json={"name": "Garden"}, headers=AUTH)
    assert category.status_code == 201
    section = client.post("/sections", json={"name": "Pump", "category_id": category.json()["id"]}, headers=AUTH)
    assert section.status_code == 201
    section_id = section.json()["id"]
    added = client.post(f"/sections/{section_id}/folders", json={"path": str(folder)}, headers=AUTH)
    assert added.status_code == 200 and added.json()["folders"] == [folder.resolve().as_posix()]
    return section_id


def test_library_flow(client: TestClient, library: Library, tmp_path: Path):
    section_id = create_section(client, write(tmp_path / "pump", {"power.md": "The pump draws 1.2 kW."}))
    started = client.post(f"/sections/{section_id}/index", headers=AUTH)
    assert started.status_code == 202 and started.json()["state"] == "indexing"
    library.wait_for_index(section_id)
    status = client.get(f"/sections/{section_id}/status", headers=AUTH).json()
    assert status["state"] == "idle" and status["report"]["added"] == 1
    assert [d["name"] for d in client.get(f"/sections/{section_id}/documents", headers=AUTH).json()] == ["power.md"]
    overview = client.get("/library", headers=AUTH).json()
    assert overview["categories"][0]["name"] == "Garden"
    assert overview["sections"][0]["documents"] == 1 and overview["sections"][0]["status"]["state"] == "idle"
    renamed = client.patch(f"/sections/{section_id}", json={"name": "Garden pump"}, headers=AUTH)
    assert renamed.json()["name"] == "Garden pump"
    assert client.delete(f"/sections/{section_id}", headers=AUTH).status_code == 204


def test_ask_streams_tokens_then_the_cited_answer(client: TestClient, library: Library, tmp_path: Path):
    section_id = create_section(client, write(tmp_path / "pump", {"power.md": "The pump draws 1.2 kW."}))
    client.post(f"/sections/{section_id}/index", headers=AUTH)
    library.wait_for_index(section_id)
    body = {"scope": {"kind": "section", "id": section_id}, "question": "How much power?", "history": []}
    response = client.post("/ask", json=body, headers=AUTH)
    assert response.status_code == 200 and response.headers["content-type"].startswith("application/x-ndjson")
    events = [json.loads(line) for line in response.text.splitlines()]
    assert "".join(e["text"] for e in events if e["type"] == "token") == "1.2 kW [1]."
    done = events[-1]
    assert done["type"] == "done" and done["grounded"] is True
    citation = done["citations"][0]
    assert citation["label"] == "power.md" and citation["section_id"] == section_id
    assert citation["source"].endswith("/pump/power.md") and "1.2 kW" in citation["snippet"]


def test_errors_are_problem_details(client: TestClient, tmp_path: Path):
    missing = client.get("/sections/nope/status", headers=AUTH)
    assert missing.status_code == 404 and missing.json()["title"] == "Not found"
    assert client.post("/categories", json={"name": ""}, headers=AUTH).status_code == 422
    category_id = client.post("/categories", json={"name": "A"}, headers=AUTH).json()["id"]
    section_id = client.post("/sections", json={"name": "S", "category_id": category_id}, headers=AUTH).json()["id"]
    bad_folder = client.post(f"/sections/{section_id}/folders", json={"path": str(tmp_path / "nope")}, headers=AUTH)
    assert bad_folder.status_code == 422 and "Not a folder" in bad_folder.json()["detail"]
    assert client.delete(f"/categories/{category_id}", headers=AUTH).status_code == 422


def test_asking_while_indexing_is_a_conflict(config, tmp_path: Path):
    models = FakeModels(HashEmbeddings(), OverlapCrossEncoder(), FakeListChatModel(responses=["-"]))
    client = make_client(Library(config, models, executor=ManualExecutor()))
    section_id = create_section(client, write(tmp_path / "pump", {"a.md": "pump"}))
    client.post(f"/sections/{section_id}/index", headers=AUTH)
    body = {"scope": {"kind": "section", "id": section_id}, "question": "pump?"}
    response = client.post("/ask", json=body, headers=AUTH)
    assert response.status_code == 409 and "Still indexing" in response.json()["detail"]
