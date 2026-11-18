from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
    version="0.1.0",
    description="Visualización educativa de cadenas de decaimiento nuclear.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
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


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
