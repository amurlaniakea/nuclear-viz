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

"""Niveles y transiciones gamma: parser con respuestas REALES de Livechart (Ni-60)."""

from pathlib import Path

import httpx
import pytest

from backend.parsers.iaea import IAEAClient, IAEAUnavailable

FIX = Path(__file__).parent / "fixtures"
LEVELS = (FIX / "livechart_levels_ni60.csv").read_text(encoding="utf-8")
GAMMAS = (FIX / "livechart_gammas_ni60.csv").read_text(encoding="utf-8")


def test_levels_basic_fields():
    r = IAEAClient.parse_levels(LEVELS, GAMMAS, 60)
    assert (r["z"], r["n"], r["a"]) == (28, 32, 60)
    assert r["total_levels"] == 5 and r["shown_levels"] == 5 and r["truncated"] is False
    ground, first = r["levels"][0], r["levels"][1]
    assert ground["idx"] == 0 and ground["energy"] == 0 and ground["half_life"] == "estable"
    assert first["energy"] == pytest.approx(1332.514) and first["jp"] == "2+"
    assert first["half_life"] == "0.735 ps"
    assert first["half_life_seconds"] == pytest.approx(7.35e-13)


def test_levels_sorted_by_energy():
    r = IAEAClient.parse_levels(LEVELS, GAMMAS, 60)
    energies = [lv["energy"] for lv in r["levels"]]
    assert energies == sorted(energies)


def test_gammas_fields_and_missing_intensity():
    r = IAEAClient.parse_levels(LEVELS, GAMMAS, 60)
    assert len(r["gammas"]) == 5
    g = r["gammas"][0]
    assert (g["start"], g["end"]) == (1, 0)
    assert g["energy"] == pytest.approx(1332.501)
    assert g["intensity"] == 100.0 and g["multipolarity"] == "E2"
    e0 = r["gammas"][-1]  # transición E0 sin intensidad
    assert e0["multipolarity"] == "E0" and e0["intensity"] is None


def test_truncation_keeps_lowest_levels_and_inner_gammas():
    r = IAEAClient.parse_levels(LEVELS, GAMMAS, 60, max_levels=3)
    assert [lv["idx"] for lv in r["levels"]] == [0, 1, 2]
    assert r["truncated"] is True and r["total_levels"] == 5 and r["shown_levels"] == 3
    assert {(g["start"], g["end"]) for g in r["gammas"]} == {(1, 0), (2, 1), (2, 0)}


def test_levels_with_energy_shift_are_omitted():
    lines = LEVELS.splitlines()
    shifted = lines[2].split(",")
    shifted[4] = "X"  # energy_shift
    text = "\n".join(lines + [",".join(shifted)])
    r = IAEAClient.parse_levels(text, GAMMAS, 60)
    assert r["omitted_shifted"] == 1 and r["total_levels"] == 5  # la fila con shift no cuenta


def test_code_zero_levels_is_none_and_zero_gammas_is_empty():
    assert IAEAClient.parse_levels("0\n", "0", 99) is None
    assert IAEAClient.parse_levels(LEVELS, "0\n", 60)["gammas"] == []


@pytest.mark.parametrize("code", ["1", "3", "6"])
def test_error_codes_raise(code):
    with pytest.raises(ValueError):
        IAEAClient.parse_levels(code, GAMMAS, 60)
    with pytest.raises(ValueError):
        IAEAClient.parse_levels(LEVELS, code, 60)


def _client(handler):
    return IAEAClient(transport=httpx.MockTransport(handler))


def test_client_requests_both_field_groups():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        seen.append(params)
        text = LEVELS if params["fields"] == "levels" else GAMMAS
        return httpx.Response(200, text=text)

    r = _client(handler).get_levels("Ni", 60, max_levels=10)
    assert [p["fields"] for p in seen] == ["levels", "gammas"]
    assert all(p["nuclides"] == "60ni" for p in seen)
    assert r["total_levels"] == 5


def test_client_no_data_and_errors():
    assert _client(lambda req: httpx.Response(200, text="0")).get_levels("Ni", 99) is None
    with pytest.raises(IAEAUnavailable):
        _client(lambda req: httpx.Response(200, text="6")).get_levels("Ni", 60)
    with pytest.raises(IAEAUnavailable):
        _client(lambda req: httpx.Response(500)).get_levels("Ni", 60)


def _with_row(text: str, row: str) -> str:
    return text.rstrip("\n") + "\n" + row + "\n"


def test_level_rows_with_empty_integer_fields_are_skipped_not_fatal():
    """Regresión: en datos reales (Ni-60 completo) había filas con campos enteros vacíos -> 502."""
    bad_idx = "28,32,Ni,,,1500.0,,,2+,1,1 ps,,,ps,1e-12,,,,,,,,,,,,,,,,31-Dec-2012,X,2026-11-27"
    bad_energy = "28,32,Ni,9,,?,,,2+,1,1 ps,,,ps,1e-12,,,,,,,,,,,,,,,,31-Dec-2012,X,2026-11-27"
    bad_z = ",,Ni,10,,1600.0,,,2+,1,1 ps,,,ps,1e-12,,,,,,,,,,,,,,,,31-Dec-2012,X,2026-11-27"
    text = _with_row(_with_row(_with_row(LEVELS, bad_idx), bad_energy), bad_z)
    r = IAEAClient.parse_levels(text, GAMMAS, 60)
    assert r["total_levels"] == 5 and [lv["idx"] for lv in r["levels"]] == [0, 1, 2, 3, 4]
    assert r["skipped_rows"] == 3


def test_gamma_rows_without_placement_are_skipped_not_fatal():
    no_end = "28,32,Ni,3,2284.8,0.04,0+,,,,,1,500.0,0.1,10,,M1,,,,,,,,,,,,,31-Dec-2012,X,2026-11-27"
    no_start = "28,32,Ni,,,,,0,0,,0+,0,700.0,0.1,10,,E2,,,,,,,,,,,,,31-Dec-2012,X,2026-11-27"
    bad_energy = "28,32,Ni,1,1332.514,0.004,2+,0,0,,0+,5,?,,10,,E2,,,,,,,,,,,,,31-Dec-2012,X,2026-11-27"
    text = _with_row(_with_row(_with_row(GAMMAS, no_end), no_start), bad_energy)
    r = IAEAClient.parse_levels(LEVELS, text, 60)
    assert len(r["gammas"]) == 5 and r["skipped_rows"] == 3


def test_complete_data_reports_zero_skipped_rows():
    assert IAEAClient.parse_levels(LEVELS, GAMMAS, 60)["skipped_rows"] == 0


def test_client_survives_incomplete_rows_end_to_end():
    bad = "28,32,Ni,,,1500.0,,,2+,1,1 ps,,,ps,1e-12,,,,,,,,,,,,,,,,31-Dec-2012,X,2026-11-27"

    def handler(request: httpx.Request) -> httpx.Response:
        text = _with_row(LEVELS, bad) if dict(request.url.params)["fields"] == "levels" else GAMMAS
        return httpx.Response(200, text=text)

    r = _client(handler).get_levels("Ni", 60)
    assert r is not None and r["shown_levels"] == 5 and r["skipped_rows"] == 1
