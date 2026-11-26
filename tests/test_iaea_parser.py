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

"""Tests del cliente IAEA con respuestas REALES de Livechart (tests/fixtures/)."""

from pathlib import Path

import httpx
import pytest

from backend.parsers.iaea import IAEAClient, IAEAUnavailable

FIX = Path(__file__).parent / "fixtures"


def _csv(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_stable_nuclide_pb206():
    r = IAEAClient.parse_csv(_csv("livechart_pb206.csv"), 206)
    assert (r["z"], r["n"], r["a"]) == (82, 124, 206)
    assert r["stable"] is True
    assert r["half_life"] == "estable"
    assert r["decay_modes"] == []


def test_minutes_and_beta_minus_pb214():
    r = IAEAClient.parse_csv(_csv("livechart_pb214.csv"), 214)
    assert r["half_life"] == "27.06 min"
    assert r["half_life_seconds"] == pytest.approx(1623.6)
    assert r["decay_modes"] == ["beta-"]
    assert r["stable"] is False


def test_years_c14():
    r = IAEAClient.parse_csv(_csv("livechart_c14.csv"), 14)
    assert r["half_life"] == "5700 y"
    assert r["decay_modes"] == ["beta-"]


def test_empty_csv_is_none():
    assert IAEAClient.parse_csv(_csv("livechart_empty.csv"), 999) is None


def test_wrong_mass_is_none():
    assert IAEAClient.parse_csv(_csv("livechart_c14.csv"), 15) is None


@pytest.mark.parametrize(
    "code,expected",
    [("A", ["alpha"]), ("B-", ["beta-"]), ("B+", ["beta+"]), ("EC", ["ec"]),
     ("EC+B+", ["ec", "beta+"]), ("SF", ["sf"]), ("IT", ["it"]), ("", [])],
)
def test_mode_codes(code, expected):
    assert IAEAClient._normalize_mode(code) == expected


def _client(handler):
    return IAEAClient(transport=httpx.MockTransport(handler))


def test_query_params_and_success():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, text=_csv("livechart_pb214.csv"))

    r = _client(handler).get_nuclide_properties("Pb", 214)
    assert seen == {"fields": "ground_states", "nuclides": "214pb"}
    assert r["half_life"] == "27.06 min"


def test_http_404_means_not_found():
    assert _client(lambda req: httpx.Response(404)).get_nuclide_properties("Pb", 1) is None


def test_http_500_is_unavailable():
    with pytest.raises(IAEAUnavailable):
        _client(lambda req: httpx.Response(500)).get_nuclide_properties("Pb", 206)


def test_network_error_is_unavailable():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(IAEAUnavailable):
        _client(handler).get_nuclide_properties("Pb", 206)


def test_garbage_csv_is_unavailable():
    with pytest.raises(IAEAUnavailable):
        _client(lambda req: httpx.Response(200, text="<html>x</html>\nfoo")).get_nuclide_properties("Pb", 206)


def test_half_life_exponent_lowercase():
    row = {"half_life": "4.468E9", "unit_hl": "Y", "half_life_sec": "1.4e17", "decay_1": "A", "decay_2": "SF"}
    r = IAEAClient._normalize(row, 92, 146)
    assert r["half_life"] == "4.468e9 y"
    assert r["decay_modes"] == ["alpha", "sf"]
