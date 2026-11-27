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

"""Geometría del esquema de niveles (site/levels.js), ejecutada con node."""

import itertools
import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
MODULE = Path(__file__).resolve().parent.parent / "site" / "levels.js"

pytestmark = pytest.mark.skipif(NODE is None, reason="node no disponible")


def _layout(data: dict) -> dict:
    script = (
        f"const m = require({json.dumps(str(MODULE))});"
        f"console.log(JSON.stringify(m.layoutLevelScheme({json.dumps(data)})));"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def _level(idx, energy, jp="2+", half_life="1 ps"):
    return {"idx": idx, "energy": energy, "jp": jp, "half_life": half_life}


NI60 = {
    "name": "Ni-60",
    "levels": [_level(0, 0.0, "0+", "estable"), _level(1, 1332.514), _level(2, 2158.632),
               _level(3, 2284.8, "0+"), _level(4, 2505.753, "4+")],
    "gammas": [
        {"start": 1, "end": 0, "energy": 1332.501, "intensity": 100.0, "multipolarity": "E2"},
        {"start": 2, "end": 1, "energy": 826.06, "intensity": 100.0, "multipolarity": "M1+E2"},
        {"start": 2, "end": 0, "energy": 2158.57, "intensity": 17.6, "multipolarity": "(E2)"},
        {"start": 3, "end": 0, "energy": 2284.87, "intensity": None, "multipolarity": "E0"},
        {"start": 9, "end": 0, "energy": 1.0, "intensity": 1.0, "multipolarity": ""},
    ],
    "shown_levels": 5, "total_levels": 375,
}


def test_ground_state_at_bottom_and_y_decreases_with_energy():
    g = _layout(NI60)
    ys = [lv["y"] for lv in g["levels"]]
    assert g["levels"][0]["ground"] is True and ys[0] == g["plot"]["bottom"]
    assert ys == sorted(ys, reverse=True) and len(set(ys)) == len(ys)
    assert g["levels"][-1]["y"] == pytest.approx(g["plot"]["top"])  # el más alto llena la escala


def test_labels_keep_minimum_gap_and_bounds():
    crowded = {"levels": [_level(i, 100.0 + i * 3) for i in range(20)] + [_level(99, 5000.0)], "gammas": []}
    g = _layout(crowded)
    label_ys = [lv["labelY"] for lv in g["levels"]]
    gaps = [a - b for a, b in itertools.pairwise(label_ys)]
    assert min(gaps) >= g["labelGap"] - 1e-6
    assert min(label_ys) >= 28 - 1e-6 and max(label_ys) <= 600 + 1e-6


def test_many_levels_shrink_gap_and_font_but_stay_ordered():
    g = _layout({"levels": [_level(i, float(i * 10)) for i in range(100)], "gammas": []})
    assert g["labelGap"] < 14 and g["labelFont"] < 11
    label_ys = [lv["labelY"] for lv in g["levels"]]
    assert all(a > b for a, b in itertools.pairwise(label_ys))


def test_gammas_connect_the_right_levels_and_ignore_unknown_ones():
    g = _layout(NI60)
    assert len(g["gammas"]) == 4  # la transición con nivel 9 inexistente se descarta
    by_idx = {lv["idx"]: lv["y"] for lv in g["levels"]}
    first = g["gammas"][0]
    assert first["y1"] == by_idx[1] and first["y2"] == by_idx[0]
    xs = [gm["x"] for gm in g["gammas"]]
    assert xs == sorted(xs) and len(set(xs)) == len(xs)
    assert all(g["plot"]["lineX1"] < x < g["plot"]["lineX2"] for x in xs)


def test_gamma_width_dashed_and_titles():
    g = _layout(NI60)
    strong = next(gm for gm in g["gammas"] if gm["energy"] == 1332.501)
    weak = next(gm for gm in g["gammas"] if gm["energy"] == 2158.57)
    unknown = next(gm for gm in g["gammas"] if gm["energy"] == 2284.87)
    assert strong["width"] > weak["width"] > unknown["width"] and unknown["dashed"] is True
    assert "E2" in strong["title"] and "I = 100" in strong["title"]


def test_level_text_and_title():
    g = _layout(NI60)
    assert g["levels"][1]["text"] == "2+ · 1332.5 keV · 1 ps"
    assert g["levels"][0]["text"] == "0+ · 0 keV · estable"
    assert g["title"] == "Ni-60 · niveles 5 de 375 (menor energía)"


def test_only_ground_state_has_no_nan():
    g = _layout({"name": "X-1", "levels": [_level(0, 0.0, "0+", "estable")], "gammas": []})
    assert g["levels"][0]["y"] == g["plot"]["bottom"] and g["ticks"] == [{"value": 0, "y": 590, "label": "0"}]


def test_empty_input():
    g = _layout({})
    assert g["levels"] == [] and g["gammas"] == []
