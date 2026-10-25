"""Carga y representación de un escenario (datos del problema).

Un escenario es un archivo JSON. Para cambiar las condiciones (nuevas zonas,
otras prioridades) basta con crear otro archivo, sin tocar el código.
"""
import copy
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict


@dataclass
class Region:
    name: str
    lat: float
    lon: float
    priority: str


@dataclass
class Zone:
    name: str
    lat: float
    lon: float
    radius: float          # grados angulares
    kind: str              # "desechos" u "objeto"


@dataclass
class Scenario:
    name: str
    description: str
    n_satellites: int
    altitude_km: float
    min_elevation_deg: float
    region_radius_km: float
    coverage_threshold: float      # fracción del disco para considerar "cubierta"
    min_separation_deg: float      # separación mínima entre satélites propios
    priority_weights: Dict[str, float]
    fitness_weights: Dict[str, float]
    regions: List[Region]
    zones: List[Zone] = field(default_factory=list)

    def weight(self, region):
        return self.priority_weights[region.priority]

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        d = copy.deepcopy(d)
        d["regions"] = [Region(**r) for r in d["regions"]]
        d["zones"] = [Zone(**z) for z in d.get("zones", [])]
        d.pop("$comment", None)
        sc = Scenario(**d)
        sc.validate()
        return sc

    def validate(self):
        """Detecta datos imposibles al cargar el escenario, antes de que
        produzcan resultados sin sentido durante la búsqueda."""
        errors = []
        if self.n_satellites < 1:
            errors.append("n_satellites debe ser al menos 1")
        if self.altitude_km <= 0 or self.region_radius_km <= 0:
            errors.append("altitude_km y region_radius_km deben ser positivos")
        if not 0 <= self.min_elevation_deg < 90:
            errors.append("min_elevation_deg debe estar en [0, 90)")
        if not 0 < self.coverage_threshold <= 1:
            errors.append("coverage_threshold debe estar en (0, 1]")
        if self.min_separation_deg < 0:
            errors.append("min_separation_deg no puede ser negativo")
        for r in self.regions:
            if r.priority not in self.priority_weights:
                errors.append(f"región {r.name}: prioridad '{r.priority}' sin peso definido")
            if not (-90 <= r.lat <= 90 and -180 <= r.lon <= 180):
                errors.append(f"región {r.name}: coordenadas fuera de rango")
        for z in self.zones:
            if z.radius <= 0:
                errors.append(f"zona {z.name}: el radio debe ser positivo")
            if z.kind not in ("desechos", "objeto"):
                errors.append(f"zona {z.name}: tipo '{z.kind}' desconocido")
            if not (-90 <= z.lat <= 90 and -180 <= z.lon <= 180):
                errors.append(f"zona {z.name}: coordenadas fuera de rango")
        if errors:
            raise ValueError(f"Escenario '{self.name}' inválido:\n  " + "\n  ".join(errors))


def load_scenario(path):
    with open(path, encoding="utf-8") as f:
        return Scenario.from_dict(json.load(f))
