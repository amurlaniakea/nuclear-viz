from __future__ import annotations

import asyncio
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.parsers.nndc import NNDCClient

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "decay_chains.json"
STATIC_DIR = BASE_DIR / "static"


def load_data() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATA_FILE.exists():
        raise RuntimeError(f"Missing data file: {DATA_FILE}")
    if not STATIC_DIR.exists():
        raise RuntimeError(f"Missing static dir: {STATIC_DIR}")
    app.state.data = load_data()
    yield


app = FastAPI(
    title="Nuclear Viz",
    version="0.3.1",
    description="Visualización educativa de cadenas de decaimiento nuclear.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cliente NNDC singleton lazy
_nndc_client: NNDCClient | None = None


def get_nndc_client() -> NNDCClient:
    global _nndc_client
    if _nndc_client is None:
        _nndc_client = NNDCClient()
    return _nndc_client


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


@app.get("/api/nuclide/{identifier}", summary="Get nuclide details from local cache or NNDC")
async def get_nuclide(identifier: str, request: Request):
    """
    Identifier format: Symbol-Mass (e.g., 'U-238', 'Pb-206')
    Tries local chains first. If not found or ?force_remote=true, queries NNDC.
    """
    # Parse identifier
    match = re.match(r"^([A-Za-z]+)-(\d+)$", identifier)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid identifier format. Use Symbol-A (e.g., U-238)")

    symbol, mass_str = match.groups()
    try:
        a = int(mass_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Mass number must be integer")

    # 1. Check local data (fast path)
    data = app.state.data
    local_nuclide = None
    for chain in data.get("chains", []):
        for nuclide in chain.get("nuclides", []):
            if nuclide["symbol"] == symbol.upper() and nuclide["a"] == a:
                local_nuclide = nuclide.copy()
                local_nuclide["source"] = "Local Educational Dataset"
                break
        if local_nuclide:
            break

    # 2. Query NNDC if requested or missing locally
    force_remote = request.query_params.get("force_remote", "").lower() in ("true", "1", "yes")

    if force_remote or not local_nuclide:
        client = get_nndc_client()
        
        # Lookup Z from symbol using hardcoded map for MVP simplicity
        z_lookup = {
            "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
            "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
            "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26, "Co": 27, "Ni": 28,
            "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34, "Br": 35, "Kr": 36,
            "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42, "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46,
            "Ag": 47, "Cd": 48, "In": 49, "Sn": 50, "Sb": 51, "Te": 52, "I": 53, "Xe": 54,
            "Cs": 55, "Ba": 56, "La": 57, "Ce": 58, "Pr": 59, "Nd": 60, "Pm": 61, "Sm": 62, "Eu": 63, "Gd": 64,
            "Tb": 65, "Dy": 66, "Ho": 67, "Er": 68, "Tm": 69, "Yb": 70, "Lu": 71, "Hf": 72, "Ta": 73, "W": 74,
            "Re": 75, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79, "Hg": 80, "Tl": 81, "Pb": 82, "Bi": 83, "Po": 84,
            "At": 85, "Rn": 86, "Fr": 87, "Ra": 88, "Ac": 89, "Th": 90, "Pa": 91, "U": 92, "Np": 93, "Pu": 94
        }
        
        z = z_lookup.get(symbol.upper())
        if not z:
             raise HTTPException(status_code=404, detail=f"Unknown element symbol '{symbol}' for remote lookup")

        # Run blocking network call in thread pool to avoid blocking event loop
        nndc_data = await asyncio.to_thread(client.get_nuclide_properties, z, a)
        
        if nndc_data:
            merged = nndc_data.copy()
            merged["id"] = f"{symbol.upper()}-{a}"
            merged["name"] = f"{symbol.upper()}-{a}" 
            merged["symbol"] = symbol.upper()
            return merged
            
        else:
            if local_nuclide:
                return local_nuclide
            raise HTTPException(status_code=404, detail=f"Nuclide {identifier} not found in local DB nor NNDC")

    return local_nuclide


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
