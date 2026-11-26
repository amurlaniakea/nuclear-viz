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

from __future__ import annotations

import asyncio
import json
import re
import time
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.parsers.iaea import IAEAClient, IAEAUnavailable

BASE_DIR = Path(__file__).resolve().parent
REMOTE_CACHE_TTL = 3600  # segundos
REMOTE_CACHE_MAX = 512
DATA_FILE = BASE_DIR / "data" / "decay_chains.json"
STATIC_DIR = BASE_DIR / "static"  # index.html del modo API
SITE_DIR = BASE_DIR.parent / "site"  # app.js, assets/ y data/ compartidos con la demo de Pages

# Mapa Z para lookup rápido (evita depender de librerías externas pesadas)
Z_LOOKUP = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
    "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28,
    "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34, "Br": 35, "Kr": 36,
    "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42, "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46,
    "Ag": 47, "Cd": 48, "In": 49, "Sn": 50, "Sb": 51, "Te": 52, "I": 53, "Xe": 54,
    "Cs": 55, "Ba": 56, "La": 57, "Ce": 58, "Pr": 59, "Nd": 60, "Pm": 61, "Sm": 62, "Eu": 63, "Gd": 64,
    "Tb": 65, "Dy": 66, "Ho": 67, "Er": 68, "Tm": 69, "Yb": 70, "Lu": 71, "Hf": 72, "Ta": 73, "W": 74,
    "Re": 75, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79, "Hg": 80, "Tl": 81, "Pb": 82, "Bi": 83, "Po": 84,
    "At": 85, "Rn": 86, "Fr": 87, "Ra": 88, "Ac": 89, "Th": 90, "Pa": 91, "U": 92, "Np": 93, "Pu": 94,
    "Am": 95, "Cm": 96, "Bk": 97, "Cf": 98, "Es": 99, "Fm": 100, "Md": 101, "No": 102, "Lr": 103,
    "Rf": 104, "Db": 105, "Sg": 106, "Bh": 107, "Hs": 108, "Mt": 109, "Ds": 110, "Rg": 111,
    "Cn": 112, "Nh": 113, "Fl": 114, "Mc": 115, "Lv": 116, "Ts": 117, "Og": 118,
}


def _app_version() -> str:
    """Versión única: la de pyproject.toml (evita desincronización)."""
    try:
        return pkg_version("nuclear-viz")
    except PackageNotFoundError:
        return "0.0.0+local"


# Identificador: Símbolo-A con sufijo opcional de isómero (p. ej. Pa-234m)
NUCLIDE_RE = re.compile(r"^([A-Za-z]{1,2})-(\d{1,3})(m\d?)?$")


def load_data() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATA_FILE.exists():
        raise RuntimeError(f"Missing data file: {DATA_FILE}")
    if not STATIC_DIR.exists():
        raise RuntimeError(f"Missing static dir: {STATIC_DIR}")
    if not (SITE_DIR / "app.js").exists():
        raise RuntimeError(f"Missing frontend assets (site/app.js) in: {SITE_DIR}")
    app.state.data = load_data()
    app.state.remote_cache = {}
    yield


app = FastAPI(
    title="Nuclear Viz",
    version=_app_version(),
    description="Visualización educativa de cadenas de decaimiento nuclear.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "nuclear-viz"}


@app.get("/api/chains")
def list_chains():
    data = app.state.data
    summaries = []
    for chain in data.get("chains", []):
        summaries.append(
            {
                "id": chain.get("id"),
                "name": chain.get("name"),
                "parent": chain.get("parent"),
                "description": chain.get("description", ""),
                "nuclide_count": len(chain.get("nuclides", [])),
                "edge_count": len(chain.get("edges", [])),
            }
        )
    return {"chains": summaries}


@app.get("/api/chains/{chain_id}")
def get_chain(chain_id: str):
    data = app.state.data
    for chain in data.get("chains", []):
        if chain.get("id") == chain_id:
            return chain
    raise HTTPException(status_code=404, detail=f"Chain '{chain_id}' not found")


@app.get("/api/nuclide/{identifier}", summary="Get nuclide details from local dataset or IAEA Livechart")
async def get_nuclide(identifier: str, request: Request):
    """
    Identifier format: Symbol-Mass (e.g., 'U-238', 'Pb-206')
    Tries local chains first. If not found or ?force_remote=true, queries IAEA Livechart (ENSDF).
    """
    match = NUCLIDE_RE.match(identifier)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid identifier format. Use Symbol-A (e.g., U-238, Pa-234m)",
        )

    raw_symbol, mass_str, isomer = match.groups()
    # Los símbolos químicos son Capitalizados ("Pb"), no MAYÚSCULAS ("PB").
    symbol = raw_symbol.capitalize()
    a = int(mass_str)
    canonical_id = f"{symbol}-{a}{isomer or ''}"

    # 1. Check local data (por id canónico: soporta isómeros como Pa-234m)
    data = app.state.data
    local_nuclide = None
    for chain in data.get("chains", []):
        for nuclide in chain.get("nuclides", []):
            if nuclide.get("id") == canonical_id:
                local_nuclide = nuclide.copy()
                local_nuclide["source"] = "Local Educational Dataset"
                break
        if local_nuclide:
            break

    # 2. Determine if we need remote
    force_remote = request.query_params.get("force_remote", "").lower() in ("true", "1", "yes")
    
    # Si hay dato local Y NO se fuerza remoto, devolver local inmediatamente
    if local_nuclide and not force_remote:
        return local_nuclide

    # Si no hay local O se fuerza remoto, ir al servicio remoto (IAEA)
    if isomer:
        # Livechart (ground_states) no distingue isómeros: no inventamos datos.
        raise HTTPException(
            status_code=404,
            detail=f"Isomer {canonical_id} is only available in the local dataset",
        )
    z = Z_LOOKUP.get(symbol)
    if not z:
        raise HTTPException(status_code=404, detail=f"Unknown element symbol '{symbol}' for remote lookup")

    # Caché TTL en memoria: evita golpear el servicio remoto con peticiones repetidas.
    cache = app.state.remote_cache
    hit = cache.get(canonical_id)
    if hit and time.monotonic() - hit[0] < REMOTE_CACHE_TTL:
        return hit[1]

    # Cliente nuevo por petición: facilita el mocking y evita estado global compartido.
    client = IAEAClient()
    try:
        try:
            remote = await asyncio.to_thread(client.get_nuclide_properties, symbol, a)
        except IAEAUnavailable:
            if local_nuclide:
                return local_nuclide  # fallback suave al dataset local
            raise HTTPException(status_code=502, detail="Remote nuclear data service unavailable")

        if remote:
            merged = remote.copy()
            merged["id"] = canonical_id
            merged["name"] = canonical_id
            merged["symbol"] = symbol
            if len(cache) >= REMOTE_CACHE_MAX:
                cache.pop(next(iter(cache)))
            cache[canonical_id] = (time.monotonic(), merged)
            return merged

        if local_nuclide:
            return local_nuclide
        raise HTTPException(status_code=404, detail=f"Nuclide {identifier} not found in local DB nor IAEA")
    finally:
        client.close()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=SITE_DIR), name="static")
