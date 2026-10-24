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
        return Scenario(**d)


def load_scenario(path):
    with open(path, encoding="utf-8") as f:
        return Scenario.from_dict(json.load(f))
