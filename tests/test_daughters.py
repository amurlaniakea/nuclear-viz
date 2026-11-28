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

"""Núcleo hijo (decays_to): cálculo y exposición en /api/nuclide."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app, daughters_for


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _clear_cache(client):
    client.app.state.remote_cache.clear()
    yield


def test_beta_minus_co60_to_ni60():
    assert daughters_for(27, 60, ["beta-"]) == [
        {"id": "Ni-60", "symbol": "Ni", "z": 28, "a": 60, "modes": ["beta-"]}
    ]


def test_alpha_u238_to_th234():
    (d,) = daughters_for(92, 238, ["alpha"])
    assert (d["id"], d["z"], d["a"]) == ("Th-234", 90, 234)


def test_beta_plus_and_ec_share_one_daughter():
    (d,) = daughters_for(11, 22, ["beta+", "ec"])  # Na-22 -> Ne-22
    assert d["id"] == "Ne-22" and d["modes"] == ["beta+", "ec"]


def test_branching_modes_give_two_daughters():
    ids = {d["id"] for d in daughters_for(83, 212, ["beta-", "alpha"])}  # Bi-212
    assert ids == {"Po-212", "Tl-208"}


@pytest.mark.parametrize(
    "z,a,modes",
    [(92, 238, ["sf"]), (82, 206, []), (82, 206, None), (6, 14, ["it", "p"]), (1, 3, ["beta+"]), (2, 4, ["alpha"])],
)
def test_no_unique_daughter(z, a, modes):
    assert daughters_for(z, a, modes) == []


def test_local_nuclides_expose_decays_to(client):
    pb214 = client.get("/api/nuclide/Pb-214").json()
    assert [d["id"] for d in pb214["decays_to"]] == ["Bi-214"]
    assert client.get("/api/nuclide/U-238").json()["decays_to"][0]["id"] == "Th-234"
    assert client.get("/api/nuclide/Pb-206").json()["decays_to"] == []
    assert client.get("/api/nuclide/Pa-234m").json()["decays_to"][0]["id"] == "U-234"


@patch("backend.main.IAEAClient")
def test_remote_nuclide_exposes_decays_to_and_is_cached(mock_cls, client):
    mock_cls.return_value.get_nuclide_properties.return_value = {
        "z": 27, "a": 60, "n": 33, "source": "IAEA Livechart (ENSDF)", "stable": False,
        "half_life": "5.2713 y", "half_life_seconds": 1.0, "decay_modes": ["beta-"], "raw_ref": "x",
    }
    first = client.get("/api/nuclide/Co-60").json()
    second = client.get("/api/nuclide/Co-60").json()
    assert first["decays_to"][0]["id"] == "Ni-60" and second["decays_to"] == first["decays_to"]
    assert mock_cls.return_value.get_nuclide_properties.call_count == 1
