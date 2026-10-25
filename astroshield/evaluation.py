"""Evaluación de una configuración (cromosoma = lista de 8 posiciones lat/lon).

Modelo de cobertura
-------------------
* Cada satélite ocupa una posición fija sobre una capa orbital a altitud h.
  Su "huella" es el casquete esférico de semiángulo lambda que lo ve con una
  elevación mínima (ver geometry.footprint_half_angle).
* Cada región es un disco de 300 km alrededor de su centro, representado por
  N puntos de muestra repartidos uniformemente en área.
* cobertura(r)   = fracción de puntos de r vistos por >= 1 satélite.
* redundancia(r) = fracción de puntos vistos por >= 2 satélites (tolerancia a
  la falla de un satélite).
* Una región se considera CUBIERTA si cobertura >= coverage_threshold,
  PARCIAL si 0 < cobertura < umbral y NO CUBIERTA si cobertura = 0.

Aptitud (0..1, mayor es mejor)
------------------------------
  F = wc * sum(w_r * cob_r) / W  +  wr * sum(w_r * red_r) / W
      + wp * sum(w_r * prox_r) / W
  donde w_r es el peso de la prioridad (Alta 3, Media 2, Normal 1),
  W = sum(w_r) y prox_r = max(0, 1 - d_r / escala) usa la distancia del
  satélite más cercano al centro de r. El término de proximidad es pequeño y
  sólo sirve de "pendiente" para que el algoritmo sepa hacia dónde moverse
  cuando aún no cubre nada (la cobertura sola es escalonada).

Restricciones
-------------
  violación = sum(max(0, radio_zona - d(sat, zona)))      (zonas y objetos)
            + sum(max(0, sep_min - d(sat_i, sat_j)))       (pares de satélites)
  En grados. Una configuración es FACTIBLE si violación == 0.
"""
import math
from dataclasses import dataclass, field
from typing import List

from . import geometry as g

N_SAMPLES = 37
FEASIBILITY_TOL = 1e-9   # violaciones menores (grados) se deben a redondeo


@dataclass
class RegionStatus:
    name: str
    priority: str
    weight: float
    coverage: float
    redundancy: float
    nearest_deg: float
    status: str               # "cubierta" | "parcial" | "no cubierta"
    sats: List[int] = field(default_factory=list)   # satélites que la ven


@dataclass
class Evaluation:
    fitness: float
    violation: float
    feasible: bool
    weighted_coverage: float
    regions: List[RegionStatus]
    violations: List[dict]

    @property
    def n_covered(self):
        return sum(1 for r in self.regions if r.status == "cubierta")


class Evaluator:
    def __init__(self, scenario, n_samples=N_SAMPLES):
        self.sc = scenario
        self.lam = g.footprint_half_angle(scenario.altitude_km, scenario.min_elevation_deg)
        self.cos_lam = math.cos(math.radians(self.lam))
        self.rho = g.km_to_deg(scenario.region_radius_km)
        # Si el satélite está más lejos que lambda + rho del centro, no puede
        # ver ningún punto de la región: se descarta sin revisar las muestras.
        self.cos_reach = math.cos(math.radians(self.lam + self.rho))
        self.regions = []
        for r in scenario.regions:
            samples = [g.to_vec(*p) for p in g.disk_samples(r.lat, r.lon, self.rho, n_samples)]
            self.regions.append((r, g.to_vec(r.lat, r.lon), samples, scenario.weight(r)))
        self.total_w = sum(w for *_, w in self.regions)
        self.zones = [(z, g.to_vec(z.lat, z.lon)) for z in scenario.zones]
        self.fw = scenario.fitness_weights
        self.n_evals = 0

    # ------------------------------------------------------------ restricciones
    def violation(self, sats, details=False):
        vecs = [g.to_vec(*s) for s in sats]
        total, info = 0.0, []
        for i, v in enumerate(vecs):
            for z, zv in self.zones:
                d = g.ang_dist_vec(v, zv)
                if d < z.radius:
                    total += z.radius - d
                    if details:
                        info.append({"type": "zona", "sat": i, "zone": z.name, "kind": z.kind,
                                     "depth_deg": round(z.radius - d, 3)})
        sep = self.sc.min_separation_deg
        if sep > 0:
            for i in range(len(vecs)):
                for j in range(i + 1, len(vecs)):
                    d = g.ang_dist_vec(vecs[i], vecs[j])
                    if d < sep:
                        total += sep - d
                        if details:
                            info.append({"type": "separacion", "sat": i, "sat2": j,
                                         "depth_deg": round(sep - d, 3)})
        return total, info

    # ------------------------------------------------------------ cobertura
    def evaluate(self, sats, details=False):
        self.n_evals += 1
        vecs = [g.to_vec(*s) for s in sats]
        fw = self.fw
        scale = fw.get("proximity_scale_deg", 90.0)
        cov_sum = red_sum = prox_sum = 0.0
        statuses = []
        for r, cv, samples, w in self.regions:
            near = [i for i, v in enumerate(vecs) if g.dot(v, cv) >= self.cos_reach]
            nearest = min(g.ang_dist_vec(v, cv) for v in vecs)
            c1 = c2 = 0
            seen_by = set()
            if near:
                for p in samples:
                    k = 0
                    for i in near:
                        if g.dot(vecs[i], p) >= self.cos_lam:
                            k += 1
                            seen_by.add(i)
                    if k >= 1:
                        c1 += 1
                    if k >= 2:
                        c2 += 1
            n = len(samples)
            cov, red = c1 / n, c2 / n
            prox = max(0.0, 1.0 - nearest / scale)
            cov_sum += w * cov
            red_sum += w * red
            prox_sum += w * prox
            if details:
                st = ("cubierta" if cov >= self.sc.coverage_threshold
                      else "parcial" if cov > 0 else "no cubierta")
                statuses.append(RegionStatus(r.name, r.priority, w, round(cov, 4), round(red, 4),
                                             round(nearest, 3), st, sorted(seen_by)))
        W = self.total_w
        wcov = cov_sum / W
        fitness = fw["coverage"] * wcov + fw["redundancy"] * red_sum / W + fw["proximity"] * prox_sum / W
        viol, info = self.violation(sats, details)
        return Evaluation(fitness, viol, viol <= FEASIBILITY_TOL, wcov, statuses, info)

    def report(self, sats):
        """Evaluación completa en forma de diccionario (para exportar)."""
        e = self.evaluate(sats, details=True)
        # un reporte no forma parte de la búsqueda: no cuenta en el presupuesto
        self.n_evals -= 1
        return {
            "fitness": round(e.fitness, 5),
            "weighted_coverage": round(e.weighted_coverage, 5),
            "violation": round(e.violation, 4),
            "feasible": e.feasible,
            "n_covered": e.n_covered,
            "regions": [r.__dict__ for r in e.regions],
            "violations": e.violations,
        }
