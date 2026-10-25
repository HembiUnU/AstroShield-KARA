"""AstroShield · interfaz de línea de comandos.

Ejemplos:
  python main.py experiments                 # todos los experimentos + datos del visor
  python main.py experiments --quick         # versión corta para probar
  python main.py run --scenario etapa2 --strategy reparacion --seed 3 --out results/mi_corrida.json
  python main.py evaluate --scenario cambio_golfo --config results/mi_corrida.json
"""
import argparse
import json
import os
import sys

from astroshield.scenario import load_scenario
from astroshield.evaluation import Evaluator
from astroshield.ga import GAConfig, run_ga, STRATEGIES

ROOT = os.path.dirname(os.path.abspath(__file__))


def scenario_path(name):
    return name if name.endswith(".json") else os.path.join(ROOT, "scenarios", name + ".json")


def print_report(rep):
    print(f"  Aptitud: {rep['fitness']}   Cobertura ponderada: {rep['weighted_coverage']}")
    print(f"  Factible: {'sí' if rep['feasible'] else 'NO'}   Violación total: {rep['violation']}°")
    for r in rep["regions"]:
        print(f"   - {r['name']:<24} [{r['priority']:<6}] {r['status']:<12} "
              f"cobertura {r['coverage']:.2f}  redundancia {r['redundancy']:.2f}  sats {r['sats']}")
    for v in rep["violations"]:
        if v["type"] == "zona":
            print(f"   ! satélite {v['sat']} invade {v['zone']} ({v['depth_deg']}°)")
        else:
            print(f"   ! satélites {v['sat']} y {v['sat2']} demasiado cerca ({v['depth_deg']}°)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="AstroShield: constelación evolutiva")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("experiments", help="corre E1-E5 y genera viewer/data.js")
    e.add_argument("--seeds", type=int, default=20)
    e.add_argument("--quick", action="store_true")

    r = sub.add_parser("run", help="una corrida del AG")
    r.add_argument("--scenario", default="etapa2")
    r.add_argument("--strategy", default="reparacion", choices=STRATEGIES)
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--generations", type=int, default=150)
    r.add_argument("--pop", type=int, default=60)
    r.add_argument("--out")

    v = sub.add_parser("evaluate", help="evalúa una configuración guardada en otro escenario")
    v.add_argument("--scenario", required=True)
    v.add_argument("--config", required=True, help="JSON con la clave 'sats' (lista de [lat, lon])")

    a = ap.parse_args(argv)
    if a.cmd == "experiments":
        from astroshield.experiments import run_all
        run_all(seeds=a.seeds, quick=a.quick)
    elif a.cmd == "run":
        sc = load_scenario(scenario_path(a.scenario))
        ev = Evaluator(sc)
        cfg = GAConfig(strategy=a.strategy, seed=a.seed, generations=a.generations, pop_size=a.pop)
        res = run_ga(ev, cfg, record_positions=False)
        rep = ev.report(res.best.sats)
        print(f"Escenario {sc.name} · estrategia {a.strategy} · semilla {a.seed} · "
              f"{res.evaluations} evaluaciones")
        print("Generación 0:")
        print_report(ev.report(res.initial_best.sats))
        print("Final:")
        print_report(rep)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                json.dump({"scenario": sc.name, "config": res.config, "sats": res.best.sats,
                           "report": rep,
                           "history": [{k: h[k] for k in ("gen", "best_fitness", "mean_fitness",
                                                          "feasible_frac")} for h in res.history]},
                          f, ensure_ascii=False, indent=1)
            print("Guardado en", a.out)
    elif a.cmd == "evaluate":
        sc = load_scenario(scenario_path(a.scenario))
        with open(a.config, encoding="utf-8") as f:
            sats = [tuple(s) for s in json.load(f)["sats"]]
        rep = Evaluator(sc).report(sats)
        print(f"Configuración evaluada en el escenario {sc.name}: {sc.description}")
        print_report(rep)
        print("=> La configuración", "SIGUE SIENDO VÁLIDA" if rep["feasible"]
              else "YA NO ES VÁLIDA bajo las nuevas condiciones")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
