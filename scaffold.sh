#!/usr/bin/env bash
set -euo pipefail

mkdir -p backend/data backend/static tests

cat > README.md <<'EOF_README'
# ☢ Nuclear Viz

Visualización educativa de física nuclear: cadenas de decaimiento, carta de núclidos y base para integrar ENSDF/EXFOR.

## MVP actual

- Cadenas naturales simplificadas:
  - Uranio-238 → Plomo-206
  - Torio-232 → Plomo-208
  - Uranio-235 → Plomo-207
- Carta interactiva N vs Z.
- Detalle de núclido, vida media y modos de decaimiento.
- API FastAPI lista para crecer hacia ENSDF/EXFOR.

## Requisitos

- Python 3.10 o superior
- python3-venv

En Debian/Ubuntu/WSL:

    sudo apt install python3-venv

## Ejecutar

    bash run.sh

Luego abrir:

    http://localhost:8000

## Tests

    ./.venv/bin/pytest

## Aviso

Los datos incluidos están simplificados con fines educativos.
No usar para protección radiológica ni cálculos de seguridad.

## Roadmap

- [ ] Parser/ingesta ENSDF.
- [ ] Consulta EXFOR.
- [ ] Diagramas de niveles gamma.
- [ ] Búsqueda global de núclidos.
- [ ] Exportar SVG/PNG.
EOF_README

cat > .gitignore <<'EOF_GITIGNORE'
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.ruff_cache/
dist/
build/
.env
.DS_Store
EOF_GITIGNORE

cat > pyproject.toml <<'EOF_PYPROJECT'
[project]
name = "nuclear-viz"
version = "0.1.0"
description = "Educational nuclear physics visualization: decay chains and nuclide chart."
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "httpx>=0.27",
  "ruff>=0.6",
]

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["backend"]

[tool.setuptools.package-data]
backend = ["data/*.json", "static/*"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"
EOF_PYPROJECT

cat > run.sh <<'EOF_RUN'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip
fi

./.venv/bin/python -m pip install -e '.[dev]'
exec ./.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
EOF_RUN
chmod +x run.sh

cat > backend/__init__.py <<'EOF_INIT'
EOF_INIT

cat > backend/main.py <<'EOF_MAIN'
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
EOF_MAIN

cat > backend/data/decay_chains.json <<'EOF_JSON'
{
  "metadata": {
    "version": "0.1.0",
    "note": "Datos simplificados con fines educativos. No usar para protección radiológica."
  },
  "chains": [
    {
      "id": "u238",
      "name": "Serie del Uranio-238 (4n+2)",
      "parent": "U-238",
      "description": "Cadena natural U-238 -> Pb-206, simplificada para docencia.",
      "nuclides": [
        {"id":"U-238","z":92,"a":238,"symbol":"U","name":"Uranio-238","half_life":"4.468e9 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Th-234","z":90,"a":234,"symbol":"Th","name":"Torio-234","half_life":"24.10 d","stable":false,"decay_modes":["beta-"]},
        {"id":"Pa-234m","z":91,"a":234,"symbol":"Pa","name":"Protactinio-234m","half_life":"1.17 min","stable":false,"decay_modes":["beta-"]},
        {"id":"U-234","z":92,"a":234,"symbol":"U","name":"Uranio-234","half_life":"2.455e5 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Th-230","z":90,"a":230,"symbol":"Th","name":"Torio-230","half_life":"7.54e4 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Ra-226","z":88,"a":226,"symbol":"Ra","name":"Radio-226","half_life":"1600 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Rn-222","z":86,"a":222,"symbol":"Rn","name":"Radón-222","half_life":"3.823 d","stable":false,"decay_modes":["alpha"]},
        {"id":"Po-218","z":84,"a":218,"symbol":"Po","name":"Polonio-218","half_life":"3.10 min","stable":false,"decay_modes":["alpha"]},
        {"id":"Pb-214","z":82,"a":214,"symbol":"Pb","name":"Plomo-214","half_life":"26.8 min","stable":false,"decay_modes":["beta-"]},
        {"id":"Bi-214","z":83,"a":214,"symbol":"Bi","name":"Bismuto-214","half_life":"19.9 min","stable":false,"decay_modes":["beta-"]},
        {"id":"Po-214","z":84,"a":214,"symbol":"Po","name":"Polonio-214","half_life":"164 us","stable":false,"decay_modes":["alpha"]},
        {"id":"Pb-210","z":82,"a":210,"symbol":"Pb","name":"Plomo-210","half_life":"22.3 y","stable":false,"decay_modes":["beta-"]},
        {"id":"Bi-210","z":83,"a":210,"symbol":"Bi","name":"Bismuto-210","half_life":"5.01 d","stable":false,"decay_modes":["beta-"]},
        {"id":"Po-210","z":84,"a":210,"symbol":"Po","name":"Polonio-210","half_life":"138.4 d","stable":false,"decay_modes":["alpha"]},
        {"id":"Pb-206","z":82,"a":206,"symbol":"Pb","name":"Plomo-206","half_life":"estable","stable":true,"decay_modes":[]}
      ],
      "edges": [
        {"from":"U-238","to":"Th-234","mode":"alpha","branch":100},
        {"from":"Th-234","to":"Pa-234m","mode":"beta-","branch":100},
        {"from":"Pa-234m","to":"U-234","mode":"beta-","branch":100},
        {"from":"U-234","to":"Th-230","mode":"alpha","branch":100},
        {"from":"Th-230","to":"Ra-226","mode":"alpha","branch":100},
        {"from":"Ra-226","to":"Rn-222","mode":"alpha","branch":100},
        {"from":"Rn-222","to":"Po-218","mode":"alpha","branch":100},
        {"from":"Po-218","to":"Pb-214","mode":"alpha","branch":100},
        {"from":"Pb-214","to":"Bi-214","mode":"beta-","branch":100},
        {"from":"Bi-214","to":"Po-214","mode":"beta-","branch":100},
        {"from":"Po-214","to":"Pb-210","mode":"alpha","branch":100},
        {"from":"Pb-210","to":"Bi-210","mode":"beta-","branch":100},
        {"from":"Bi-210","to":"Po-210","mode":"beta-","branch":100},
        {"from":"Po-210","to":"Pb-206","mode":"alpha","branch":100}
      ]
    },
    {
      "id": "th232",
      "name": "Serie del Torio-232 (4n)",
      "parent": "Th-232",
      "description": "Cadena natural Th-232 -> Pb-208, simplificada para docencia.",
      "nuclides": [
        {"id":"Th-232","z":90,"a":232,"symbol":"Th","name":"Torio-232","half_life":"1.405e10 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Ra-228","z":88,"a":228,"symbol":"Ra","name":"Radio-228","half_life":"5.75 y","stable":false,"decay_modes":["beta-"]},
        {"id":"Ac-228","z":89,"a":228,"symbol":"Ac","name":"Actinio-228","half_life":"6.15 h","stable":false,"decay_modes":["beta-"]},
        {"id":"Th-228","z":90,"a":228,"symbol":"Th","name":"Torio-228","half_life":"1.91 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Ra-224","z":88,"a":224,"symbol":"Ra","name":"Radio-224","half_life":"3.63 d","stable":false,"decay_modes":["alpha"]},
        {"id":"Rn-220","z":86,"a":220,"symbol":"Rn","name":"Radón-220","half_life":"55.6 s","stable":false,"decay_modes":["alpha"]},
        {"id":"Po-216","z":84,"a":216,"symbol":"Po","name":"Polonio-216","half_life":"0.145 s","stable":false,"decay_modes":["alpha"]},
        {"id":"Pb-212","z":82,"a":212,"symbol":"Pb","name":"Plomo-212","half_life":"10.64 h","stable":false,"decay_modes":["beta-"]},
        {"id":"Bi-212","z":83,"a":212,"symbol":"Bi","name":"Bismuto-212","half_life":"60.55 min","stable":false,"decay_modes":["beta-","alpha"]},
        {"id":"Po-212","z":84,"a":212,"symbol":"Po","name":"Polonio-212","half_life":"0.30 us","stable":false,"decay_modes":["alpha"]},
        {"id":"Tl-208","z":81,"a":208,"symbol":"Tl","name":"Talio-208","half_life":"3.05 min","stable":false,"decay_modes":["beta-"]},
        {"id":"Pb-208","z":82,"a":208,"symbol":"Pb","name":"Plomo-208","half_life":"estable","stable":true,"decay_modes":[]}
      ],
      "edges": [
        {"from":"Th-232","to":"Ra-228","mode":"alpha","branch":100},
        {"from":"Ra-228","to":"Ac-228","mode":"beta-","branch":100},
        {"from":"Ac-228","to":"Th-228","mode":"beta-","branch":100},
        {"from":"Th-228","to":"Ra-224","mode":"alpha","branch":100},
        {"from":"Ra-224","to":"Rn-220","mode":"alpha","branch":100},
        {"from":"Rn-220","to":"Po-216","mode":"alpha","branch":100},
        {"from":"Po-216","to":"Pb-212","mode":"alpha","branch":100},
        {"from":"Pb-212","to":"Bi-212","mode":"beta-","branch":100},
        {"from":"Bi-212","to":"Po-212","mode":"beta-","branch":64},
        {"from":"Bi-212","to":"Tl-208","mode":"alpha","branch":36},
        {"from":"Po-212","to":"Pb-208","mode":"alpha","branch":100},
        {"from":"Tl-208","to":"Pb-208","mode":"beta-","branch":100}
      ]
    },
    {
      "id": "u235",
      "name": "Serie del Actinio (U-235, 4n+3)",
      "parent": "U-235",
      "description": "Cadena natural U-235 -> Pb-207, simplificada para docencia.",
      "nuclides": [
        {"id":"U-235","z":92,"a":235,"symbol":"U","name":"Uranio-235","half_life":"7.04e8 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Th-231","z":90,"a":231,"symbol":"Th","name":"Torio-231","half_life":"25.5 h","stable":false,"decay_modes":["beta-"]},
        {"id":"Pa-231","z":91,"a":231,"symbol":"Pa","name":"Protactinio-231","half_life":"3.276e4 y","stable":false,"decay_modes":["alpha"]},
        {"id":"Ac-227","z":89,"a":227,"symbol":"Ac","name":"Actinio-227","half_life":"21.77 y","stable":false,"decay_modes":["beta-"]},
        {"id":"Th-227","z":90,"a":227,"symbol":"Th","name":"Torio-227","half_life":"18.7 d","stable":false,"decay_modes":["alpha"]},
        {"id":"Ra-223","z":88,"a":223,"symbol":"Ra","name":"Radio-223","half_life":"11.43 d","stable":false,"decay_modes":["alpha"]},
        {"id":"Rn-219","z":86,"a":219,"symbol":"Rn","name":"Radón-219","half_life":"3.96 s","stable":false,"decay_modes":["alpha"]},
        {"id":"Po-215","z":84,"a":215,"symbol":"Po","name":"Polonio-215","half_life":"1.78 ms","stable":false,"decay_modes":["alpha"]},
        {"id":"Pb-211","z":82,"a":211,"symbol":"Pb","name":"Plomo-211","half_life":"36.1 min","stable":false,"decay_modes":["beta-"]},
        {"id":"Bi-211","z":83,"a":211,"symbol":"Bi","name":"Bismuto-211","half_life":"2.14 min","stable":false,"decay_modes":["alpha"]},
        {"id":"Tl-207","z":81,"a":207,"symbol":"Tl","name":"Talio-207","half_life":"4.77 min","stable":false,"decay_modes":["beta-"]},
        {"id":"Pb-207","z":82,"a":207,"symbol":"Pb","name":"Plomo-207","half_life":"estable","stable":true,"decay_modes":[]}
      ],
      "edges": [
        {"from":"U-235","to":"Th-231","mode":"alpha","branch":100},
        {"from":"Th-231","to":"Pa-231","mode":"beta-","branch":100},
        {"from":"Pa-231","to":"Ac-227","mode":"alpha","branch":100},
        {"from":"Ac-227","to":"Th-227","mode":"beta-","branch":100},
        {"from":"Th-227","to":"Ra-223","mode":"alpha","branch":100},
        {"from":"Ra-223","to":"Rn-219","mode":"alpha","branch":100},
        {"from":"Rn-219","to":"Po-215","mode":"alpha","branch":100},
        {"from":"Po-215","to":"Pb-211","mode":"alpha","branch":100},
        {"from":"Pb-211","to":"Bi-211","mode":"beta-","branch":100},
        {"from":"Bi-211","to":"Tl-207","mode":"alpha","branch":100},
        {"from":"Tl-207","to":"Pb-207","mode":"beta-","branch":100}
      ]
    }
  ]
}
EOF_JSON

cat > backend/static/index.html <<'EOF_HTML'
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Nuclear Viz</title>
  <link rel="stylesheet" href="/static/style.css" />
</head>
<body>
  <header>
    <h1>☢ Nuclear Viz</h1>
    <p>Visualización educativa de cadenas de decaimiento nuclear</p>
  </header>

  <main>
    <section class="controls">
      <label for="chain-select">Cadena:</label>
      <select id="chain-select"></select>

      <div class="legend">
        <span class="legend-item"><span class="swatch alpha"></span>α</span>
        <span class="legend-item"><span class="swatch beta-minus"></span>β−</span>
        <span class="legend-item"><span class="swatch beta-plus"></span>β+/EC</span>
        <span class="legend-item"><span class="swatch stable"></span>estable</span>
      </div>
    </section>

    <section class="layout">
      <div id="chart" aria-label="Carta de núclidos de la cadena seleccionada"></div>
      <aside id="detail">Cargando...</aside>
    </section>

    <section class="table-section">
      <h2>Núclidos</h2>
      <table id="nuclide-table">
        <thead>
          <tr>
            <th>Núclido</th>
            <th>Z</th>
            <th>N</th>
            <th>A</th>
            <th>Vida media</th>
            <th>Modos</th>
            <th>Estable</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </section>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
EOF_HTML

cat > backend/static/style.css <<'EOF_CSS'
:root {
  color-scheme: dark;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  background: #020617;
  color: #e2e8f0;
}

header {
  padding: 24px 28px 8px;
}

h1 {
  margin: 0 0 6px;
  font-size: 2rem;
}

header p {
  margin: 0;
  color: #94a3b8;
}

main {
  padding: 20px 28px 40px;
  display: grid;
  gap: 18px;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border: 1px solid #1e293b;
  border-radius: 14px;
  background: #0f172a;
}

label {
  color: #94a3b8;
}

select {
  background: #020617;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 10px;
  min-width: min(420px, 100%);
}

.legend {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-left: auto;
  color: #cbd5e1;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.swatch {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  display: inline-block;
}

.swatch.alpha {
  background: #f97316;
}

.swatch.beta-minus {
  background: #38bdf8;
}

.swatch.beta-plus {
  background: #a78bfa;
}

.swatch.stable {
  background: #22c55e;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
}

#chart {
  min-height: 720px;
  border: 1px solid #1e293b;
  border-radius: 14px;
  background: #020617;
  overflow: auto;
}

#detail {
  padding: 16px;
  border: 1px solid #1e293b;
  border-radius: 14px;
  background: #0f172a;
  min-height: 720px;
  line-height: 1.45;
}

#detail h2 {
  margin-top: 0;
  font-size: 1.25rem;
}

.detail-label {
  color: #94a3b8;
  font-size: 0.92rem;
  margin-top: 12px;
}

.pill {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px 6px 2px 0;
  border-radius: 999px;
  border: 1px solid #334155;
  background: #020617;
}

#detail ul {
  margin: 8px 0;
  padding-left: 18px;
}

#detail li {
  margin: 4px 0;
}

.table-section {
  border: 1px solid #1e293b;
  border-radius: 14px;
  background: #0f172a;
  padding: 16px;
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 10px;
  border-bottom: 1px solid #1e293b;
  text-align: left;
}

th {
  color: #94a3b8;
  font-size: 0.92rem;
}

tbody tr:hover,
tbody tr.selected {
  background: #082f49;
  cursor: pointer;
}

svg text {
  user-select: none;
}

.nuclide {
  cursor: pointer;
}

.nuclide:focus {
  outline: 2px solid #facc15;
}

.radioactive-node {
  fill: #082f49;
}

.stable-node {
  fill: #052e16;
}

@media (max-width: 1000px) {
  .layout {
    grid-template-columns: 1fr;
  }

  #detail {
    min-height: 220px;
  }
}
EOF_CSS

cat > backend/static/app.js <<'EOF_JS'
const chartEl = document.getElementById('chart');
const detailEl = document.getElementById('detail');
const selectEl = document.getElementById('chain-select');

const MODE_COLORS = {
  alpha: '#f97316',
  'beta-': '#38bdf8',
  'beta+': '#a78bfa',
  gamma: '#94a3b8',
  stable: '#22c55e'
};

let currentChain = null;
let selectedNuclideId = null;

document.addEventListener('DOMContentLoaded', init);

async function init() {
  try {
    const res = await fetch('/api/chains');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    const chains = payload.chains || [];

    if (!chains.length) {
      detailEl.textContent = 'No hay cadenas disponibles.';
      return;
    }

    selectEl.innerHTML = '';
    for (const chain of chains) {
      const option = document.createElement('option');
      option.value = chain.id;
      option.textContent = chain.name;
      selectEl.appendChild(option);
    }

    selectEl.addEventListener('change', async () => {
      await loadChain(selectEl.value);
    });

    await loadChain(chains[0].id);
  } catch (error) {
    detailEl.textContent = `Error cargando datos: ${error.message}`;
  }
}

async function loadChain(chainId) {
  try {
    const res = await fetch(`/api/chains/${encodeURIComponent(chainId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentChain = await res.json();
    selectedNuclideId = currentChain.parent || currentChain.nuclides?.[0]?.id || null;
    renderAll();
  } catch (error) {
    detailEl.textContent = `Error cargando cadena: ${error.message}`;
  }
}

function renderAll() {
  renderChart();
  renderTable();
  renderDetail(selectedNuclideId);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) {
    el.setAttribute(key, String(value));
  }
  return el;
}

function scaler(min, max, rangeMin, rangeMax) {
  const span = (max - min) || 1;
  return (value) => rangeMin + ((value - min) / span) * (rangeMax - rangeMin);
}

function makeTicks(min, max, targetCount) {
  const span = max - min;
  if (span <= 0) return [min];

  const step = Math.max(1, Math.round(span / Math.max(1, targetCount)));
  const ticks = [];
  const start = Math.ceil(min / step) * step;

  for (let value = start; value <= max; value += step) {
    ticks.push(value);
  }

  return ticks;
}

function addMarker(defs, id, color) {
  const marker = svgEl('marker', {
    id,
    markerWidth: 10,
    markerHeight: 10,
    refX: 8,
    refY: 4,
    orient: 'auto'
  });

  const path = svgEl('path', {
    d: 'M0,0 L8,4 L0,8 z',
    fill: color
  });

  marker.appendChild(path);
  defs.appendChild(marker);
}

function edgeColor(mode) {
  if (mode === 'alpha') return MODE_COLORS.alpha;
  if (mode === 'beta-') return MODE_COLORS['beta-'];
  if (mode === 'beta+' || mode === 'ec') return MODE_COLORS['beta+'];
  return MODE_COLORS.gamma;
}

function markerForMode(mode) {
  if (mode === 'alpha') return 'url(#arrow-alpha)';
  if (mode === 'beta-') return 'url(#arrow-beta-minus)';
  if (mode === 'beta+' || mode === 'ec') return 'url(#arrow-beta-plus)';
  return '';
}

function renderChart() {
  chartEl.innerHTML = '';
  if (!currentChain) return;

  const width = 1100;
  const height = 760;
  const margin = { top: 30, right: 40, bottom: 78, left: 78 };

  const nuclides = (currentChain.nuclides || []).map((item) => ({
    ...item,
    n: item.a - item.z
  }));

  if (!nuclides.length) {
    chartEl.textContent = 'Sin núclidos para esta cadena.';
    return;
  }

  const byId = Object.fromEntries(nuclides.map((item) => [item.id, item]));

  const minX = Math.min(...nuclides.map((item) => item.n)) - 3;
  const maxX = Math.max(...nuclides.map((item) => item.n)) + 3;
  const minY = Math.min(...nuclides.map((item) => item.z)) - 3;
  const maxY = Math.max(...nuclides.map((item) => item.z)) + 3;

  const xScale = scaler(minX, maxX, margin.left, width - margin.right);
  const yScale = scaler(minY, maxY, height - margin.bottom, margin.top);

  const svg = svgEl('svg', {
    viewBox: `0 0 ${width} ${height}`,
    width: '100%',
    height: '100%'
  });

  const defs = svgEl('defs');
  addMarker(defs, 'arrow-alpha', MODE_COLORS.alpha);
  addMarker(defs, 'arrow-beta-minus', MODE_COLORS['beta-']);
  addMarker(defs, 'arrow-beta-plus', MODE_COLORS['beta+']);
  svg.appendChild(defs);

  const xTicks = makeTicks(minX, maxX, 8);
  const yTicks = makeTicks(minY, maxY, 8);

  for (const tick of xTicks) {
    const x = xScale(tick);

    svg.appendChild(svgEl('line', {
      x1: x,
      y1: margin.top,
      x2: x,
      y2: height - margin.bottom,
      stroke: '#0f172a',
      'stroke-width': 1
    }));

    const text = svgEl('text', {
      x,
      y: height - margin.bottom + 24,
      fill: '#64748b',
      'font-size': 12,
      'text-anchor': 'middle'
    });

    text.textContent = tick;
    svg.appendChild(text);
  }

  for (const tick of yTicks) {
    const y = yScale(tick);

    svg.appendChild(svgEl('line', {
      x1: margin.left,
      y1: y,
      x2: width - margin.right,
      y2: y,
      stroke: '#0f172a',
      'stroke-width': 1
    }));

    const text = svgEl('text', {
      x: margin.left - 12,
      y: y + 4,
      fill: '#64748b',
      'font-size': 12,
      'text-anchor': 'end'
    });

    text.textContent = tick;
    svg.appendChild(text);
  }

  const xLabel = svgEl('text', {
    x: width / 2,
    y: height - 16,
    fill: '#94a3b8',
    'font-size': 15,
    'text-anchor': 'middle'
  });
  xLabel.textContent = 'Número de neutrones N';
  svg.appendChild(xLabel);

  const yLabel = svgEl('text', {
    x: 18,
    y: height / 2,
    fill: '#94a3b8',
    'font-size': 15,
    'text-anchor': 'middle',
    transform: `rotate(-90 18 ${height / 2})`
  });
  yLabel.textContent = 'Número atómico Z';
  svg.appendChild(yLabel);

  for (const edge of currentChain.edges || []) {
    const source = byId[edge.from];
    const target = byId[edge.to];
    if (!source || !target) continue;

    const x1 = xScale(source.n);
    const y1 = yScale(source.z);
    const x2 = xScale(target.n);
    const y2 = yScale(target.z);

    const dx = x2 - x1;
    const dy = y2 - y1;
    const dist = Math.hypot(dx, dy) || 1;

    const padStart = 24;
    const padEnd = 32;

    const sx = x1 + (dx / dist) * padStart;
    const sy = y1 + (dy / dist) * padStart;
    const tx = x2 - (dx / dist) * padEnd;
    const ty = y2 - (dy / dist) * padEnd;

    const line = svgEl('line', {
      x1: sx,
      y1: sy,
      x2: tx,
      y2: ty,
      stroke: edgeColor(edge.mode),
      'stroke-width': 2.75,
      opacity: 0.92
    });

    const marker = markerForMode(edge.mode);
    if (marker) line.setAttribute('marker-end', marker);

    const title = svgEl('title');
    title.textContent = `${edge.from} -> ${edge.to} (${edge.mode}${edge.branch ? `, branch ${edge.branch}%` : ''})`;
    line.appendChild(title);
    svg.appendChild(line);
  }

  for (const nuclide of nuclides) {
    const x = xScale(nuclide.n);
    const y = yScale(nuclide.z);
    const selected = nuclide.id === selectedNuclideId;

    const g = svgEl('g', {
      class: 'nuclide',
      tabindex: 0
    });

    const circle = svgEl('circle', {
      cx: x,
      cy: y,
      r: 20,
      class: nuclide.stable ? 'stable-node' : 'radioactive-node'
    });

    circle.setAttribute(
      'stroke',
      selected ? '#facc15' : nuclide.stable ? '#22c55e' : '#64748b'
    );
    circle.setAttribute('stroke-width', selected ? 4 : 2);

    const symbolText = svgEl('text', {
      x,
      y: y + 5,
      fill: '#e2e8f0',
      'font-size': 13,
      'font-weight': 700,
      'text-anchor': 'middle'
    });
    symbolText.textContent = nuclide.symbol;

    const massText = svgEl('text', {
      x,
      y: y + 38,
      fill: '#94a3b8',
      'font-size': 12,
      'text-anchor': 'middle'
    });
    massText.textContent = nuclide.a;

    const title = svgEl('title');
    title.textContent = `${nuclide.name} | Z=${nuclide.z}, N=${nuclide.n}, A=${nuclide.a} | Vida media: ${nuclide.half_life || 'desconocida'}`;

    g.appendChild(circle);
    g.appendChild(symbolText);
    g.appendChild(massText);
    g.appendChild(title);

    g.addEventListener('click', () => {
      selectedNuclideId = nuclide.id;
      renderChart();
      renderTable();
      renderDetail(nuclide.id);
    });

    svg.appendChild(g);
  }

  chartEl.appendChild(svg);
}

function renderTable() {
  const tbody = document.querySelector('#nuclide-table tbody');
  if (!tbody || !currentChain) return;

  tbody.innerHTML = '';

  for (const nuclide of currentChain.nuclides || []) {
    const tr = document.createElement('tr');

    if (nuclide.id === selectedNuclideId) {
      tr.classList.add('selected');
    }

    const modes = (nuclide.decay_modes || []).join(', ') || '-';

    tr.innerHTML = `
      <td>${escapeHtml(nuclide.name || nuclide.id)}</td>
      <td>${nuclide.z}</td>
      <td>${nuclide.a - nuclide.z}</td>
      <td>${nuclide.a}</td>
      <td>${escapeHtml(nuclide.half_life || '-')}</td>
      <td>${escapeHtml(modes)}</td>
      <td>${nuclide.stable ? 'sí' : 'no'}</td>
    `;

    tr.addEventListener('click', () => {
      selectedNuclideId = nuclide.id;
      renderChart();
      renderTable();
      renderDetail(nuclide.id);
    });

    tbody.appendChild(tr);
  }
}

function renderDetail(nuclideId) {
  if (!currentChain) return;

  const nuclide = (currentChain.nuclides || []).find((item) => item.id === nuclideId);

  if (!nuclide) {
    detailEl.innerHTML = '<p>Selecciona un núclido.</p>';
    return;
  }

  const outgoing = (currentChain.edges || []).filter((edge) => edge.from === nuclide.id);
  const incoming = (currentChain.edges || []).filter((edge) => edge.to === nuclide.id);

  const modes = (nuclide.decay_modes || [])
    .map((mode) => `<span class="pill">${escapeHtml(mode)}</span>`)
    .join('') || '<span class="pill">-</span>';

  const outgoingHtml = outgoing.length
    ? outgoing
        .map((edge) => {
          return `<li>${escapeHtml(edge.to)} <span class="pill">${escapeHtml(edge.mode)}</span>${
            edge.branch ? ` (${edge.branch}%)` : ''
          }</li>`;
        })
        .join('')
    : '<li>-</li>';

  const incomingHtml = incoming.length
    ? incoming
        .map((edge) => {
          return `<li>${escapeHtml(edge.from)} <span class="pill">${escapeHtml(edge.mode)}</span>${
            edge.branch ? ` (${edge.branch}%)` : ''
          }</li>`;
        })
        .join('')
    : '<li>-</li>';

  detailEl.innerHTML = `
    <h2>${escapeHtml(nuclide.name || nuclide.id)}</h2>

    <div class="detail-label">Cadena</div>
    <div>${escapeHtml(currentChain.name)}</div>

    <div class="detail-label">Z / N / A</div>
    <div>${nuclide.z} / ${nuclide.a - nuclide.z} / ${nuclide.a}</div>

    <div class="detail-label">Vida media</div>
    <div>${escapeHtml(nuclide.half_life || '-')}</div>

    <div class="detail-label">Modos de decaimiento</div>
    <div>${modes}</div>

    <div class="detail-label">Decaimientos salientes</div>
    <ul>${outgoingHtml}</ul>

    <div class="detail-label">Decaimientos entrantes</div>
    <ul>${incomingHtml}</ul>

    <div class="detail-label">Nota</div>
    <div>
      Los datos de esta cadena están simplificados con fines educativos.
      La siguiente etapa conectará ENSDF/EXFOR.
    </div>
  `;
}
EOF_JS

cat > tests/__init__.py <<'EOF_TESTS_INIT'
EOF_TESTS_INIT

cat > tests/test_api.py <<'EOF_TESTS'
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_chains(client):
    response = client.get("/api/chains")
    assert response.status_code == 200
    payload = response.json()
    assert "chains" in payload
    assert len(payload["chains"]) >= 3


def test_chain_detail_u238(client):
    response = client.get("/api/chains/u238")
    assert response.status_code == 200
    chain = response.json()
    assert chain["id"] == "u238"
    assert len(chain["nuclides"]) >= 10
    assert len(chain["edges"]) >= 10


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Nuclear Viz" in response.text
EOF_TESTS

echo "Scaffold creado. Archivos principales:"
find . -maxdepth 3 -type f | sort
