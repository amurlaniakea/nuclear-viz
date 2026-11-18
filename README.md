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
