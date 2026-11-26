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

import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NNDC_BASE_URL = "https://www.nndc.bnl.gov/endb/rest/v1"


class NNDCClient:
    """
    Cliente mínimo para la API REST del National Nuclear Data Center (NNDC).
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def get_nuclide_properties(self, z: int, a: int) -> dict[str, Any] | None:
        """
        Obtiene propiedades básicas de un núclido desde NNDC.
        """
        url = f"{NNDC_BASE_URL}/nuclide/{z}/{a}/properties"
        
        try:
            response = self.client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            
            raw_data = response.json()
            return self._normalize(raw_data, z, a)
            
        except httpx.HTTPStatusError as exc:
            logger.warning(f"HTTP Error {exc.response.status_code} for {z}-{a}")
            return None
        except httpx.RequestError as exc:
            logger.warning(f"Connection Error for {z}-{a}: {exc}")
            return None
        except json.JSONDecodeError as exc:
            logger.warning(f"JSON Decode Error for {z}-{a}: {exc}")
            return None
        except (KeyError, TypeError, ValueError) as exc:
            # Errores de estructura de datos inesperada
            logger.warning(f"Data Structure Error for {z}-{a}: {exc}")
            return None

    def _normalize(self, raw: dict[str, Any], z: int, a: int) -> dict[str, Any]:
        result = {
            "z": z,
            "a": a,
            "n": a - z,
            "source": "NNDC",
            "stable": False,
            "half_life": None,
            "decay_modes": [],
            "raw_ref": f"https://www.nndc.bnl.gov/chart/#display={z},{a}"
        }

        properties = raw.get("properties", {})
        
        stability_info = properties.get("stability", {})
        is_stable_str = stability_info.get("isStable", "")
        if isinstance(is_stable_str, str):
            result["stable"] = is_stable_str.lower() == "yes"
        elif isinstance(is_stable_str, bool):
            result["stable"] = is_stable_str
        
        half_life_info = properties.get("halfLife", {})
        hl_value = half_life_info.get("value")
        hl_unit = half_life_info.get("unit", "")
        
        if hl_value is not None:
            unit_map = {"s": "s", "m": "min", "h": "h", "d": "d", "y": "y"}
            clean_unit = unit_map.get(hl_unit, hl_unit)
            result["half_life"] = f"{hl_value} {clean_unit}"
        
        decay_info = properties.get("decayModes", [])
        modes = []
        if isinstance(decay_info, list):
            for mode_item in decay_info:
                m_type = mode_item.get("type", "")
                if m_type:
                    normalized = self._normalize_mode_name(m_type)
                    if normalized and normalized not in modes:
                        modes.append(normalized)
        
        result["decay_modes"] = modes
        
        return result

    @staticmethod
    def _normalize_mode_name(name: str) -> str | None:
        # Coincidencia por palabra completa: antes "ec" casaba dentro de "decay"/"spectrum".
        n = name.lower()
        if "alpha" in n:
            return "alpha"
        if "beta-" in n or "electron emission" in n:
            return "beta-"
        if "beta+" in n or "positron" in n:
            return "beta+"
        if "electron capture" in n or re.search(r"\bec\b", n):
            return "ec"
        if "gamma" in n:
            return "gamma"
        if "spontaneous fission" in n or re.search(r"\bsf\b", n):
            return "sf"
        return None

    def close(self):
        self.client.close()
