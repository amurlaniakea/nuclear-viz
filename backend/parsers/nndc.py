from __future__ import annotations

from typing import Any

import httpx

NNDC_BASE_URL = "https://www.nndc.bnl.gov/endb/rest/v1"


class NNDCClient:
    """
    Cliente mínimo para la API REST del National Nuclear Data Center (NNDC).
    Endpoint usado: /nuclide/{Z}/{A}/properties
    
    Nota: La API puede cambiar. Se recomienda cachear respuestas en producción.
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def get_nuclide_properties(self, z: int, a: int) -> dict[str, Any] | None:
        """
        Obtiene propiedades básicas de un núclido desde NNDC.
        
        Args:
            z: Número atómico (protones)
            a: Número másico
            
        Returns:
            Diccionario con datos normalizados o None si falla/no existe.
        """
        url = f"{NNDC_BASE_URL}/nuclide/{z}/{a}/properties"
        
        try:
            response = self.client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            
            raw_data = response.json()
            return self._normalize(raw_data, z, a)
            
        except httpx.HTTPError as exc:
            # En producción, usar logger.warning en lugar de print
            print(f"[NNDCClient] Error fetching {z}-{a}: {exc}")
            return None
        except Exception as exc:
            print(f"[NNDCClient] Unexpected error parsing {z}-{a}: {exc}")
            return None

    def _normalize(self, raw: dict[str, Any], z: int, a: int) -> dict[str, Any]:
        """
        Normaliza la respuesta cruda de NNDC a nuestro esquema interno.
        """
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
        
        # Estabilidad
        stability_info = properties.get("stability", {})
        is_stable_str = stability_info.get("isStable", "")
        if isinstance(is_stable_str, str):
            result["stable"] = is_stable_str.lower() == "yes"
        elif isinstance(is_stable_str, bool):
            result["stable"] = is_stable_str
        
        # Vida media
        half_life_info = properties.get("halfLife", {})
        hl_value = half_life_info.get("value")
        hl_unit = half_life_info.get("unit", "")
        
        if hl_value is not None:
            unit_map = {"s": "s", "m": "min", "h": "h", "d": "d", "y": "y"}
            clean_unit = unit_map.get(hl_unit, hl_unit)
            result["half_life"] = f"{hl_value} {clean_unit}"
        
        # Modos de decaimiento
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
        name_lower = name.lower()
        if "alpha" in name_lower:
            return "alpha"
        if "beta-" in name_lower or "electron emission" in name_lower:
            return "beta-"
        if "beta+" in name_lower or "positron" in name_lower:
            return "beta+"
        if "electron capture" in name_lower or "ec" in name_lower:
            return "ec"
        if "gamma" in name_lower:
            return "gamma"
        if "spontaneous fission" in name_lower or "sf" in name_lower:
            return "sf"
        return None

    def close(self):
        self.client.close()
