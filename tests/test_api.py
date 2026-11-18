import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_chains(client):
    response = client.get("/api/chains")
    assert response.status_code == 200
    payload = response.json()
    assert "chains" in payload
    assert len(payload["chains"]) >= 3


def test_chain_detail_u238(client):
    response = client.get("/api/chains/u238")
    assert response.status_code == 200
    chain = response.json()
    assert chain["id"] == "u238"
    assert len(chain["nuclides"]) >= 10
    assert len(chain["edges"]) >= 10


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Nuclear Viz" in response.text
