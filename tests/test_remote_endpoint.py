# SPDX-FileCopyrightText: 2026 Pedro Sordo Martínez <amurlaniakea@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Copyright (C) 2026 Pedro Sordo Martínez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see
# <https://www.gnu.org/licenses/>.

from unittest.mock import patch

import pytest
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


@pytest.fixture(autouse=True)
def _clear_remote_cache(client):
    client.app.state.remote_cache.clear()
    yield


def _remote(**over):
    base = {
        "z": 92, "a": 238, "n": 146, "source": "IAEA Livechart (ENSDF)", "stable": False,
        "half_life": "4.468e9 y", "half_life_seconds": None, "decay_modes": ["alpha"],
        "raw_ref": "...",
    }
    base.update(over)
    return base


@patch("backend.main.IAEAClient")
def test_force_remote_mocked(mock_cls, client):
    mock_cls.return_value.get_nuclide_properties.return_value = _remote()
    response = client.get("/api/nuclide/U-238?force_remote=true")
    assert response.status_code == 200
    assert response.json()["source"] == "IAEA Livechart (ENSDF)"
    mock_cls.return_value.get_nuclide_properties.assert_called_once_with("U", 238)


@patch("backend.main.IAEAClient")
def test_remote_when_missing_local(mock_cls, client):
    mock_cls.return_value.get_nuclide_properties.return_value = _remote(
        z=6, a=14, n=8, half_life="5700 y", decay_modes=["beta-"]
    )
    response = client.get("/api/nuclide/C-14")
    assert response.status_code == 200
    assert response.json()["id"] == "C-14"


@patch("backend.main.IAEAClient")
def test_remote_result_is_cached(mock_cls, client):
    mock_cls.return_value.get_nuclide_properties.return_value = _remote(z=6, a=14, n=8)
    client.get("/api/nuclide/C-14")
    client.get("/api/nuclide/C-14")
    assert mock_cls.return_value.get_nuclide_properties.call_count == 1


@patch("backend.main.IAEAClient")
def test_remote_not_found_is_404(mock_cls, client):
    mock_cls.return_value.get_nuclide_properties.return_value = None
    assert client.get("/api/nuclide/C-99").status_code == 404


@patch("backend.main.IAEAClient")
def test_remote_unavailable_is_502(mock_cls, client):
    from backend.parsers.iaea import IAEAUnavailable

    mock_cls.return_value.get_nuclide_properties.side_effect = IAEAUnavailable("boom")
    assert client.get("/api/nuclide/C-14").status_code == 502


@patch("backend.main.IAEAClient")
def test_remote_unavailable_falls_back_to_local(mock_cls, client):
    from backend.parsers.iaea import IAEAUnavailable

    mock_cls.return_value.get_nuclide_properties.side_effect = IAEAUnavailable("boom")
    response = client.get("/api/nuclide/U-238?force_remote=true")
    assert response.status_code == 200
    assert response.json()["source"] == "Local Educational Dataset"


def test_heavy_element_symbol_accepted(client):
    with patch("backend.main.IAEAClient") as mock_cls:
        mock_cls.return_value.get_nuclide_properties.return_value = _remote(z=95, a=241, n=146)
        assert client.get("/api/nuclide/Am-241").status_code == 200


# --- Regresiones de la auditoría (2026-11-26) ---

@pytest.mark.parametrize("ident", ["Th-234", "Pb-206", "Ra-226", "Pb-214"])
def test_two_letter_symbols_resolve_locally(client, ident):
    """Antes: 'Pb' -> 'PB' no casaba con el dataset ni con Z_LOOKUP (404)."""
    response = client.get(f"/api/nuclide/{ident}")
    assert response.status_code == 200
    assert response.json()["source"] == "Local Educational Dataset"


def test_symbol_case_insensitive(client):
    assert client.get("/api/nuclide/pb-206").json()["id"] == "Pb-206"


def test_metastable_isomer_local(client):
    response = client.get("/api/nuclide/Pa-234m")
    assert response.status_code == 200
    assert response.json()["id"] == "Pa-234m"


def test_isomer_not_sent_to_remote(client):
    response = client.get("/api/nuclide/Tc-99m")
    assert response.status_code == 404


