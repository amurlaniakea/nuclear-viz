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
