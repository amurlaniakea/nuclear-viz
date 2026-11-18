import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_get_local_nuclide(client):
    """Should find U-238 in local educational dataset."""
    response = client.get("/api/nuclide/U-238")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "U-238"
    assert data["source"] == "Local Educational Dataset"
    assert data["z"] == 92
    assert data["a"] == 238


def test_invalid_identifier_format(client):
    response = client.get("/api/nuclide/INVALID")
    assert response.status_code == 400


def test_unknown_element_symbol(client):
    # X is not a valid symbol in our simplified lookup
    response = client.get("/api/nuclide/X-100")
    # It might fall back to 404 because it's not in local AND fails lookup
    assert response.status_code == 404


@patch("backend.main.NNDCClient")
def test_force_remote_mocked(mock_nndc_cls, client):
    """Test forcing remote query with mocked successful response."""
    mock_instance = MagicMock()
    mock_nndc_cls.return_value = mock_instance
    
    # Mock return value simulating NNDC structure normalized
    mock_instance.get_nuclide_properties.return_value = {
        "z": 92,
        "a": 238,
        "n": 146,
        "source": "NNDC",
        "stable": False,
        "half_life": "4.468e9 y",
        "decay_modes": ["alpha"],
        "raw_ref": "..."
    }

    response = client.get("/api/nuclide/U-238?force_remote=true")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "NNDC"
    assert data["half_life"] == "4.468e9 y"
    
    # Verify call happened
    mock_instance.get_nuclide_properties.assert_called_once_with(92, 238)


@patch("backend.main.NNDCClient")
def test_remote_fallback_on_missing_local(mock_nndc_cls, client):
    """If not in local, should try remote automatically."""
    mock_instance = MagicMock()
    mock_nndc_cls.return_value = mock_instance
    
    # Assume C-14 is NOT in our small local chains (we only have U/Th/Pb series mostly)
    # Actually C-14 isn't in decay_chains.json provided earlier.
    mock_instance.get_nuclide_properties.return_value = {
        "z": 6,
        "a": 14,
        "n": 8,
        "source": "NNDC",
        "stable": False,
        "half_life": "5730 y",
        "decay_modes": ["beta-"],
        "raw_ref": "..."
    }

    response = client.get("/api/nuclide/C-14")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "NNDC"
    assert data["id"] == "C-14"
