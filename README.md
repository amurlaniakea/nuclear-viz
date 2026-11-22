# ☢ Nuclear Viz

## 🌐 Live Demo

Visita la demo estática en: [https://amurlaniakea.github.io/nuclear-viz/](https://amurlaniakea.github.io/nuclear-viz/)

Esta demo utiliza datos pre-generados en `site/data/`. Para probar la integración completa con NNDC, ejecuta el backend localmente.


[![CI](https://github.com/amurlaniakea/nuclear-viz/actions/workflows/ci.yml/badge.svg)](https://github.com/amurlaniakea/nuclear-viz/actions/workflows/ci.yml)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

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

## 📧 Contacto

- **Autor**: Pedro Sordo Martínez
- **e-mail**: amurlaniakea@gmail.com
- **Hugging Face**: [MagoPredator](https://huggingface.co/MagoPredator)

## Licencia

AGPL-3.0-or-later. Ver [`LICENSE`](LICENSE).

## Verificación

- `pytest` valida la API y las invariantes de los datos de decaimiento.
- Los datos incluidos están simplificados y acotados a fines educativos.
- No usar para protección radiológica ni cálculos de seguridad.