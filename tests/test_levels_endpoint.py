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

"""Endpoint /api/nuclide/{id}/levels (cliente IAEA simulado)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.parsers.iaea import IAEAUnavailable


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _clear_cache(client):
    client.app.state.remote_cache.clear()
    yield


DATA = {
    "z": 28, "n": 32, "a": 60, "source": "IAEA Livechart (ENSDF)",
    "levels": [{"idx": 0, "energy": 0.0, "jp": "0+", "half_life": "estable", "half_life_seconds": None}],
    "gammas": [], "total_levels": 1, "shown_levels": 1, "truncated": False,
    "omitted_shifted": 0, "raw_ref": "...",
}


@patch("backend.main.IAEAClient")
def test_levels_ok_and_defaults(mock_cls, client):
    mock_cls.return_value.get_levels.return_value = dict(DATA)
    r = client.get("/api/nuclide/ni-60/levels")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "Ni-60" and body["symbol"] == "Ni" and body["levels"][0]["idx"] == 0
    mock_cls.return_value.get_levels.assert_called_once_with("Ni", 60, 40)


@patch("backend.main.IAEAClient")
def test_levels_max_levels_param_and_cache(mock_cls, client):
    mock_cls.return_value.get_levels.return_value = dict(DATA)
    client.get("/api/nuclide/Ni-60/levels?max_levels=10")
    client.get("/api/nuclide/Ni-60/levels?max_levels=10")
    assert mock_cls.return_value.get_levels.call_count == 1
    client.get("/api/nuclide/Ni-60/levels?max_levels=20")
    assert mock_cls.return_value.get_levels.call_count == 2


@pytest.mark.parametrize("value", ["4", "101", "abc"])
def test_levels_max_levels_validation(client, value):
    assert client.get(f"/api/nuclide/Ni-60/levels?max_levels={value}").status_code == 422


@patch("backend.main.IAEAClient")
def test_levels_not_found_is_404(mock_cls, client):
    mock_cls.return_value.get_levels.return_value = None
    assert client.get("/api/nuclide/Ni-99/levels").status_code == 404


@patch("backend.main.IAEAClient")
def test_levels_unavailable_is_502(mock_cls, client):
    mock_cls.return_value.get_levels.side_effect = IAEAUnavailable("boom")
    assert client.get("/api/nuclide/Ni-60/levels").status_code == 502


def test_levels_bad_format_isomer_and_unknown_symbol(client):
    assert client.get("/api/nuclide/hola/levels").status_code == 400
    assert client.get("/api/nuclide/Pa-234m/levels").status_code == 404
    assert client.get("/api/nuclide/Zz-10/levels").status_code == 404
