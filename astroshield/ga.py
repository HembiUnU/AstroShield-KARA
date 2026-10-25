"""Algoritmo evolutivo (algoritmo genético con codificación real).

Representación: un individuo es una lista de 8 genes; cada gen es la posición
(lat, lon) de un satélite. Todos los satélites forman parte del mismo
cromosoma, por lo que se evalúan siempre como una configuración completa.

Ciclo por generación:
  1. Selección por torneo (k individuos, gana el de mejor "clave").
  2. Cruce alineado: se empareja cada satélite del padre A con el más cercano
     del padre B y se intercambian pares al azar (cruce uniforme). Así el
     hijo no hereda dos satélites para la misma región por accidente.
  3. Mutación: cada satélite, con probabilidad pm, se desplaza una distancia
     |N(0, sigma)| en un rumbo aleatorio; sigma decrece linealmente
     (exploración al principio, ajuste fino al final). Con probabilidad
     baja se reubica al azar (evita estancamiento) y con otra probabilidad
     baja se reubica cerca de una región elegida al azar ("reubicación
     dirigida", operador específico del problema que permite mover un
     satélite sobrante a otra región en un solo paso).
  4. (Opcional) reparación de restricciones.
  5. Reemplazo generacional con elitismo (los mejores pasan sin cambios).

Manejo de restricciones (estrategia):
  ignorar      -> se ordena sólo por aptitud (Etapa 1, o para mostrar el
                  efecto de no considerar restricciones).
  penalizacion -> aptitud - k * violación.
  deb          -> reglas de factibilidad de Deb: factible > infactible;
                  entre factibles gana la mayor aptitud; entre infactibles,
                  la menor violación.
  reparacion   -> reglas de Deb + cada hijo se repara empujando los
                  satélites fuera de las zonas prohibidas.
"""
import random
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from . import geometry as g

STRATEGIES = ("ignorar", "penalizacion", "deb", "reparacion")


@dataclass
class GAConfig:
    pop_size: int = 60
    generations: int = 150
    tournament: int = 3
    crossover_rate: float = 0.9
    mutation_rate: float = 0.2       # probabilidad por satélite
    sigma_start: float = 12.0        # grados
    sigma_end: float = 0.5
    reset_rate: float = 0.02         # reubicación aleatoria por satélite
    targeted_rate: float = 0.02      # reubicación dirigida (cerca de una región)
    elitism: int = 2
    strategy: str = "reparacion"
    penalty_k: float = 0.05          # por grado de violación
    seed: int = 1

    def __post_init__(self):
        # sin esta revisión, una estrategia mal escrita se comportaría como
        # "deb" sin avisar (ver make_key)
        if self.strategy not in STRATEGIES:
            raise ValueError(f"estrategia '{self.strategy}' desconocida; opciones: {STRATEGIES}")
        if self.pop_size < 2 or self.generations < 1:
            raise ValueError("pop_size debe ser >= 2 y generations >= 1")
        if not 0 <= self.elitism < self.pop_size:
            raise ValueError("elitism debe estar en [0, pop_size)")
        if not 1 <= self.tournament <= self.pop_size:
            raise ValueError("tournament debe estar en [1, pop_size]")
        if self.reset_rate + self.targeted_rate + self.mutation_rate > 1:
            raise ValueError("reset_rate + targeted_rate + mutation_rate no puede pasar de 1")


@dataclass
class Individual:
    sats: list
    fitness: float = 0.0
    violation: float = 0.0
    feasible: bool = True
    key: tuple = ()


@dataclass
class RunResult:
    best: Individual
    initial_best: Individual
    history: List[dict] = field(default_factory=list)
    evaluations: int = 0
    config: dict = field(default_factory=dict)
    final_population: list = field(default_factory=list)


def make_key(fit, viol, feasible, cfg):
    if cfg.strategy == "ignorar":
        return (fit,)
    if cfg.strategy == "penalizacion":
        return (fit - cfg.penalty_k * viol,)
    return (1, fit) if feasible else (0, -viol)


class GA:
    def __init__(self, evaluator, cfg: GAConfig):
        self.ev = evaluator
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.n = evaluator.sc.n_satellites

    # ------------------------------------------------------------ utilidades
    def assess(self, sats):
        e = self.ev.evaluate(sats)
        ind = Individual([tuple(s) for s in sats], e.fitness, e.violation, e.feasible)
        ind.key = make_key(e.fitness, e.violation, e.feasible, self.cfg)
        return ind

    def random_config(self):
        return [g.random_point(self.rng) for _ in range(self.n)]

    def tournament(self, pop):
        return max(self.rng.sample(pop, self.cfg.tournament), key=lambda i: i.key)

    # ------------------------------------------------------------ operadores
    def crossover(self, a, b):
        if self.rng.random() > self.cfg.crossover_rate:
            return list(a), list(b)
        # emparejamiento voraz: cada satélite de A con el más cercano libre de B
        va = [g.to_vec(*s) for s in a]
        vb = [g.to_vec(*s) for s in b]
        pairs = sorted(((g.dot(va[i], vb[j]), i, j) for i in range(self.n) for j in range(self.n)),
                       reverse=True)
        used_a, used_b, match = set(), set(), {}
        for _, i, j in pairs:
            if i not in used_a and j not in used_b:
                match[i] = j
                used_a.add(i)
                used_b.add(j)
        c1, c2 = list(a), [None] * self.n
        for i, j in match.items():
            if self.rng.random() < 0.5:
                c1[i], c2[i] = b[j], a[i]
            else:
                c2[i] = b[j]
        return c1, c2

    def mutate(self, sats, gen):
        cfg = self.cfg
        t = gen / max(1, cfg.generations - 1)
        sigma = cfg.sigma_start + (cfg.sigma_end - cfg.sigma_start) * t
        out = []
        for s in sats:
            r = self.rng.random()
            if r < cfg.reset_rate:
                s = g.random_point(self.rng)
            elif r < cfg.reset_rate + cfg.targeted_rate:
                # salto a una región elegida al azar (dentro de la distancia
                # que permite cubrirla por completo): permite mover un satélite
                # sobrante de una región a otra en un solo paso
                reg = self.rng.choice(self.ev.sc.regions)
                reach = max(0.1, self.ev.lam - self.ev.rho)
                s = g.destination(reg.lat, reg.lon, self.rng.uniform(0, 360),
                                  reach * self.rng.random() ** 0.5)
            elif r < cfg.reset_rate + cfg.targeted_rate + cfg.mutation_rate:
                s = g.destination(s[0], s[1], self.rng.uniform(0, 360), abs(self.rng.gauss(0, sigma)))
            out.append(s)
        return out

    def repair(self, sats, max_iter=10):
        """Empuja cada satélite fuera de las zonas prohibidas y separa pares
        demasiado cercanos. Movimiento mínimo: sobre la línea zona->satélite."""
        sats = list(sats)
        margin = 0.05
        sep = self.ev.sc.min_separation_deg
        for _ in range(max_iter):
            moved = False
            for i, s in enumerate(sats):
                for z, zv in self.ev.zones:
                    d = g.ang_dist_vec(g.to_vec(*s), zv)
                    if d < z.radius:
                        brg = (g.bearing(z.lat, z.lon, s[0], s[1]) if d > 1e-6
                               else self.rng.uniform(0, 360))
                        s = g.destination(z.lat, z.lon, brg, z.radius + margin)
                        moved = True
                sats[i] = s
            for i in range(self.n):
                for j in range(i + 1, self.n):
                    a, b = sats[i], sats[j]
                    d = g.ang_dist(a[0], a[1], b[0], b[1])
                    if d < sep:
                        brg = (g.bearing(a[0], a[1], b[0], b[1]) if d > 1e-6
                               else self.rng.uniform(0, 360))
                        sats[j] = g.destination(a[0], a[1], brg, sep + margin)
                        moved = True
            if not moved:
                break
        return sats

    # ------------------------------------------------------------ ciclo
    def run(self, initial: Optional[list] = None, record_positions=True) -> RunResult:
        cfg = self.cfg
        self.ev.n_evals = 0
        configs = [list(c) for c in (initial or [])][:cfg.pop_size]
        while len(configs) < cfg.pop_size:
            configs.append(self.random_config())
        if cfg.strategy == "reparacion":
            configs = [self.repair(c) for c in configs]
        pop = [self.assess(c) for c in configs]
        best = max(pop, key=lambda i: i.key)
        initial_best = best
        history = [self._snapshot(0, pop, best, record_positions)]

        for gen in range(1, cfg.generations):
            pop.sort(key=lambda i: i.key, reverse=True)
            new = pop[:cfg.elitism]
            while len(new) < cfg.pop_size:
                p1, p2 = self.tournament(pop), self.tournament(pop)
                for child in self.crossover(p1.sats, p2.sats):
                    child = self.mutate(child, gen)
                    if cfg.strategy == "reparacion":
                        child = self.repair(child)
                    new.append(self.assess(child))
            pop = new[:cfg.pop_size]
            cand = max(pop, key=lambda i: i.key)
            if cand.key > best.key:
                best = cand
            history.append(self._snapshot(gen, pop, best, record_positions))

        return RunResult(best, initial_best, history, self.ev.n_evals, asdict(cfg),
                         [i.sats for i in sorted(pop, key=lambda i: i.key, reverse=True)])

    def _snapshot(self, gen, pop, best, record_positions):
        fits = [i.fitness for i in pop]
        h = {"gen": gen,
             "best_fitness": round(best.fitness, 5),
             "best_violation": round(best.violation, 4),
             "mean_fitness": round(sum(fits) / len(fits), 5),
             "feasible_frac": round(sum(i.feasible for i in pop) / len(pop), 3)}
        if record_positions:
            h["best_sats"] = [[round(a, 3), round(b, 3)] for a, b in best.sats]
        return h


def run_ga(evaluator, cfg: GAConfig, initial=None, record_positions=True):
    return GA(evaluator, cfg).run(initial, record_positions)


def random_search(evaluator, n_evals, strategy="deb", seed=1, penalty_k=0.05):
    """Línea base: configuraciones aleatorias con el mismo presupuesto de
    evaluaciones que el AG. Sirve para demostrar que la evolución aporta."""
    cfg = GAConfig(strategy=strategy, seed=seed, penalty_k=penalty_k)
    ga = GA(evaluator, cfg)
    best = None
    for _ in range(n_evals):
        c = ga.random_config()
        if strategy == "reparacion":
            c = ga.repair(c)
        ind = ga.assess(c)
        if best is None or ind.key > best.key:
            best = ind
    return best


def heuristic_reference(evaluator):
    """Solución construida a mano: un satélite en el centro de cada región y
    los sobrantes junto a las regiones de mayor peso (separados sep_min).
    Si un centro cae en zona prohibida, se repara. Sirve como referencia."""
    sc = evaluator.sc
    regs = sorted(sc.regions, key=lambda r: -sc.weight(r))
    sats = [(r.lat, r.lon) for r in sc.regions]
    k = 0
    while len(sats) < sc.n_satellites:
        r = regs[k % len(regs)]
        sats.append(g.destination(r.lat, r.lon, 90.0, sc.min_separation_deg + 0.05))
        k += 1
    ga = GA(evaluator, GAConfig(seed=0))
    return ga.repair(sats[:sc.n_satellites])
