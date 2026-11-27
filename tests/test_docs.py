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

"""La documentación no se desincroniza del código."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from backend.main import app

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_readme_documents_every_api_route():
    routes = {r.path for r in app.routes if r.path.startswith("/api/")}
    assert routes, "no se encontraron rutas /api/"
    for path in routes:
        prefix = path.split("{")[0]  # "/api/nuclide/{identifier}" -> "/api/nuclide/"
        assert prefix in README, f"README no documenta {path}"


def test_readme_images_exist():
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", README)
    local = [rel for rel in images if not rel.startswith(("http://", "https://"))]
    assert local, "el README debería incluir al menos una imagen local"
    for rel in local:
        assert (ROOT / rel).exists(), f"imagen del README inexistente: {rel}"


def test_example_svgs_are_valid_exports():
    files = sorted((ROOT / "docs" / "ejemplos").glob("nuclear-viz-*.svg"))
    assert len(files) == 3
    for f in files:
        root = ET.parse(f).getroot()
        assert root.tag == "{http://www.w3.org/2000/svg}svg"
        assert "Nuclear Viz" in "".join(root.itertext())
