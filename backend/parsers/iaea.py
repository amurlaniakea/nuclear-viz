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

from __future__ import annotations

import csv
import io
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

IAEA_URL = "https://nds.iaea.org/relnsd/v1/data"
IAEA_SOURCE = "IAEA Livechart (ENSDF)"
IAEA_CHART_URL = "https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html"

# Códigos de unidad de Livechart (vistos: "m" = minutos, "Y" = años) -> etiqueta legible.
_UNIT_MAP = {
    "y": "y", "d": "d", "h": "h", "m": "min", "s": "s",
    "ms": "ms", "us": "µs", "ns": "ns", "ps": "ps", "fs": "fs", "as": "as",
}

# Códigos de modo de decaimiento -> nombres que ya usa el dataset local y el frontend.
# Verificado contra la API real: "B-". El resto sigue la notación ENSDF habitual.
_MODE_MAP = {
    "A": ["alpha"],
    "B-": ["beta-"],
    "B+": ["beta+"],
    "EC": ["ec"],
    "EC+B+": ["ec", "beta+"],
    "SF": ["sf"],
}


class IAEAUnavailable(Exception):
    """El servicio remoto no respondió o devolvió algo inutilizable (≠ núclido inexistente)."""


class IAEAClient:
    """
    Cliente mínimo para la API pública de datos de IAEA Livechart
    (https://nds.iaea.org/relnsd/vcharthtml/api_v0_guide.html), con datos de ENSDF.
    Devuelve CSV; aquí se extrae el estado fundamental de un núclido.
    """

    def __init__(self, timeout: float = 10.0, transport: httpx.BaseTransport | None = None):
        self.client = httpx.Client(timeout=timeout, transport=transport)

    def get_nuclide_properties(self, symbol: str, a: int) -> dict[str, Any] | None:
        """None = el núclido no existe en IAEA. IAEAUnavailable = fallo de red/formato."""
        params = {"fields": "ground_states", "nuclides": f"{a}{symbol.lower()}"}
        try:
            response = self.client.get(IAEA_URL, params=params)
        except httpx.RequestError as exc:
            logger.warning("IAEA connection error for %s-%s: %s", symbol, a, exc)
            raise IAEAUnavailable(str(exc)) from exc

        if response.status_code in (400, 404):
            return None
        if response.status_code != 200:
            logger.warning("IAEA HTTP %s for %s-%s", response.status_code, symbol, a)
            raise IAEAUnavailable(f"HTTP {response.status_code}")

        try:
            return self.parse_csv(response.text, a)
        except (KeyError, ValueError) as exc:
            logger.warning("IAEA unexpected CSV for %s-%s: %s", symbol, a, exc)
            raise IAEAUnavailable("unexpected CSV format") from exc

    @classmethod
    def parse_csv(cls, text: str, a: int) -> dict[str, Any] | None:
        for row in csv.DictReader(io.StringIO(text)):
            z, n = int(row["z"]), int(row["n"])
            if z + n != a or (row.get("energy") or "0").strip() not in ("0", "0.0"):
                continue  # solo el estado fundamental del A pedido
            return cls._normalize(row, z, n)
        return None

    @classmethod
    def _normalize(cls, row: dict[str, str], z: int, n: int) -> dict[str, Any]:
        a = z + n
        raw_hl = (row.get("half_life") or "").strip()
        # Livechart devuelve "4.468E9": se muestra como "4.468e9".
        raw_hl = re.sub(r"(?<=\d)E(?=[+-]?\d)", "e", raw_hl)
        unit = (row.get("unit_hl") or "").strip()
        stable = raw_hl.upper() == "STABLE"

        if stable:
            half_life: str | None = "estable"
        elif raw_hl:
            half_life = f"{raw_hl} {_UNIT_MAP.get(unit.lower(), unit)}".strip()
        else:
            half_life = None

        try:
            seconds = float(row["half_life_sec"]) if (row.get("half_life_sec") or "").strip() else None
        except ValueError:
            seconds = None

        modes: list[str] = []
        for key in ("decay_1", "decay_2", "decay_3"):
            for mode in cls._normalize_mode(row.get(key) or ""):
                if mode not in modes:
                    modes.append(mode)

        return {
            "z": z,
            "a": a,
            "n": n,
            "source": IAEA_SOURCE,
            "stable": stable,
            "half_life": half_life,
            "half_life_seconds": seconds,
            "decay_modes": modes,
            "raw_ref": IAEA_CHART_URL,
        }

    @staticmethod
    def _normalize_mode(code: str) -> list[str]:
        code = code.strip().upper()
        if not code:
            return []
        # Códigos no mapeados se conservan en minúsculas (no se pierde información).
        return list(_MODE_MAP.get(code, [code.lower()]))

    def close(self):
        self.client.close()
