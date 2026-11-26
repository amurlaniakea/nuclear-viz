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

"""El frontend (app.js, estilos, favicon) tiene una única fuente: site/."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_no_duplicated_frontend_assets():
    for name in ("app.js", "style.css", "favicon.svg"):
        assert not (ROOT / "backend" / "static" / name).exists(), f"duplicado: backend/static/{name}"


def test_index_modes_declared():
    assert 'name="nv-mode" content="api"' in (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
    assert 'name="nv-mode" content="static"' in (ROOT / "site/index.html").read_text(encoding="utf-8")


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "/static/app.js" in r.text


def test_shared_assets_served(client):
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/assets/style.css").status_code == 200
    assert client.get("/static/assets/favicon.svg").status_code == 200


def test_app_js_has_both_modes(client):
    js = client.get("/static/app.js").text
    assert "/api/chains" in js and "./data/chains_index.json" in js


MOTTO = "«Tecnósfera al servicio de la Biósfera.» — «La Paz Es El Camino.»"


@pytest.mark.parametrize("index", ["backend/static/index.html", "site/index.html"])
def test_header_has_motto_first_and_yellow_icon(index):
    html = (ROOT / index).read_text(encoding="utf-8")
    header = html[html.index("<header>"):html.index("</header>")]
    assert header.index(MOTTO) < header.index("<h1>"), "el lema debe ir en la primera línea"
    assert '<span class="logo-icon"' in header.split("<h1>")[1]


def test_logo_icon_is_yellow():
    css = (ROOT / "site/assets/style.css").read_text(encoding="utf-8")
    assert ".logo-icon" in css and "#facc15" in css


def test_search_form_only_in_api_mode():
    api = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
    static = (ROOT / "site/index.html").read_text(encoding="utf-8")
    assert 'id="nuclide-search"' in api and "/static/nuclide-search.js" in api
    assert api.index("nuclide-search.js") < api.index("/static/app.js")
    assert 'id="nuclide-search"' not in static


def test_search_assets_served_and_wired(client):
    assert client.get("/static/nuclide-search.js").status_code == 200
    js = client.get("/static/app.js").text
    assert "/api/nuclide/" in js and "initSearch" in js


@pytest.mark.parametrize(
    "index,script",
    [("backend/static/index.html", "/static/export.js"), ("site/index.html", "./export.js")],
)
def test_export_buttons_and_script_in_both_modes(index, script):
    html = (ROOT / index).read_text(encoding="utf-8")
    assert 'id="export-svg"' in html and 'id="export-png"' in html
    assert html.index(script) < html.index("app.js")


def test_export_assets_served_and_wired(client):
    assert client.get("/static/export.js").status_code == 200
    assert "initExport" in client.get("/static/app.js").text


def test_static_demo_explains_search_needs_server():
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    assert "requiere el servidor local" in html
