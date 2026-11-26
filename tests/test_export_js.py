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

"""Helpers puros de site/export.js, ejecutados con node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
MODULE = Path(__file__).resolve().parent.parent / "site" / "export.js"

pytestmark = pytest.mark.skipif(NODE is None, reason="node no disponible")


def _run(expr: str):
    script = f"const m = require({json.dumps(str(MODULE))}); console.log(JSON.stringify({expr}));"
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize(
    "chain_id,ext,expected",
    [
        ("u238", "svg", "nuclear-viz-u238.svg"),
        ("Th-232", "png", "nuclear-viz-th-232.png"),
        ("../../etc/passwd", "svg", "nuclear-viz-etc-passwd.svg"),
        ("a b/c d", "png", "nuclear-viz-a-b-c-d.png"),
        ("", "svg", "nuclear-viz-cadena.svg"),
        (None, "png", "nuclear-viz-cadena.png"),
    ],
)
def test_export_file_name(chain_id, ext, expected):
    assert _run(f"m.exportFileName({json.dumps(chain_id)}, {json.dumps(ext)})") == expected


def test_class_fills_cover_node_classes():
    assert set(_run("m.CLASS_FILLS")) == {"stable-node", "radioactive-node"}
