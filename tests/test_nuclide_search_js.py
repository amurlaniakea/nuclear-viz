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

"""Lógica pura de la búsqueda (site/nuclide-search.js), ejecutada con node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
MODULE = Path(__file__).resolve().parent.parent / "site" / "nuclide-search.js"

pytestmark = pytest.mark.skipif(NODE is None, reason="node no disponible")


def _run(expr: str):
    script = f"const m = require({json.dumps(str(MODULE))}); console.log(JSON.stringify({expr}));"
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Pb-214", "Pb-214"),
        ("pb214", "Pb-214"),
        ("  PB - 214 ", "Pb-214"),
        ("214Pb", "Pb-214"),
        ("214-pb", "Pb-214"),
        ("Pa-234m", "Pa-234m"),
        ("234mPa", "Pa-234m"),
        ("99mTc", "Tc-99m"),
        ("U238", "U-238"),
        ("C-14", "C-14"),
        ("", None),
        ("Pb", None),
        ("214", None),
        ("Pb-0", None),
        ("Pb-9999", None),
        ("Plomo-214", None),
        ("../etc/passwd", None),
        ("<script>", None),
    ],
)
def test_parse_nuclide_query(text, expected):
    assert _run(f"m.parseNuclideQuery({json.dumps(text)})") == expected


@pytest.mark.parametrize("status", [400, 404, 502, 500])
def test_error_messages_are_nonempty(status):
    assert len(_run(f"m.errorMessage({status}, 'Pb-214')")) > 10
