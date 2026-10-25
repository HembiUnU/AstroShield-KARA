"""Experimentos reproducibles que respaldan los resultados.

E1  Etapa 1 (sin restricciones): AG vs búsqueda aleatoria, N semillas.
E2  Etapa 2 (con restricciones): 4 estrategias de manejo de restricciones
    + búsqueda aleatoria, N semillas.
E3  ¿La mejor configuración de la Etapa 1 sigue siendo válida en la Etapa 2?
E4  Cambios de condiciones: validez de la configuración anterior y
    re-optimización en frío (desde cero) vs en caliente (desde la población
    anterior, con la tercera parte de generaciones).
E5  Sensibilidad de parámetros (tasa de mutación, elitismo, tamaño de población).

Todos los resultados se guardan en results/ y se exportan al visor 3D
(viewer/data.js), de modo que el globo muestra exactamente lo que produjo
la ejecución.
"""
import csv
import json
import os
import statistics as stats
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from .scenario import load_scenario
from .evaluation import Evaluator
from .ga import GAConfig, run_ga, random_search, heuristic_reference, STRATEGIES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCEN = os.path.join(ROOT, "scenarios")
RES = os.path.join(ROOT, "results")
VIEW = os.path.join(ROOT, "viewer")

CHANGES = ["cambio_golfo", "cambio_prioridades", "cambio_japon"]


def scen(name):
    return load_scenario(os.path.join(SCEN, name + ".json"))


# ------------------------------------------------------------------ trabajos
# (funciones de nivel superior para poder usarlas en procesos paralelos)

def job_ga(args):
    scen_name, cfg, initial = args
    ev = Evaluator(scen(scen_name))
    r = run_ga(ev, cfg, initial, record_positions=False)
    rep = ev.report(r.best.sats)
    gen_090 = next((h["gen"] for h in r.history
                    if h["best_fitness"] >= 0.90
                    and (cfg.strategy == "ignorar" or h["best_violation"] == 0)), None)
    return {"scenario": scen_name, "method": "AG-" + cfg.strategy, "seed": cfg.seed,
            "fitness": rep["fitness"], "feasible": rep["feasible"], "violation": rep["violation"],
            "n_covered": rep["n_covered"], "weighted_coverage": rep["weighted_coverage"],
            "evaluations": r.evaluations, "gen_reach_090": gen_090,
            "curve": [h["best_fitness"] for h in r.history],
            "mean_curve": [h["mean_fitness"] for h in r.history],
            "feasible_curve": [h["feasible_frac"] for h in r.history],
            "best_sats": r.best.sats}


def job_random(args):
    scen_name, n_evals, strategy, seed = args
    ev = Evaluator(scen(scen_name))
    b = random_search(ev, n_evals, strategy=strategy, seed=seed)
    rep = ev.report(b.sats)
    return {"scenario": scen_name, "method": "Aleatoria", "seed": seed,
            "fitness": rep["fitness"], "feasible": rep["feasible"], "violation": rep["violation"],
            "n_covered": rep["n_covered"], "weighted_coverage": rep["weighted_coverage"],
            "evaluations": n_evals, "gen_reach_090": None, "best_sats": b.sats}


def summarize(rows, label=None):
    f = [r["fitness"] for r in rows]
    feas = [r for r in rows if r["feasible"]]
    reach = [r["gen_reach_090"] for r in rows if r.get("gen_reach_090") is not None]
    return {
        "label": label or rows[0]["method"],
        "runs": len(rows),
        "fitness_mean": round(stats.mean(f), 4),
        "fitness_std": round(stats.pstdev(f), 4),
        "fitness_min": round(min(f), 4),
        "fitness_max": round(max(f), 4),
        "feasible_pct": round(100 * len(feas) / len(rows), 1),
        "covered_mean": round(stats.mean(r["n_covered"] for r in rows), 2),
        "violation_mean": round(stats.mean(r["violation"] for r in rows), 3),
        "gen_reach_090_mean": round(stats.mean(reach), 1) if reach else None,
        "reach_090_pct": round(100 * len(reach) / len(rows), 1),
    }


def mean_curve(rows, key="curve"):
    n = len(rows[0][key])
    return [round(stats.mean(r[key][i] for r in rows), 5) for i in range(n)]


# ------------------------------------------------------------------ ejecución visible

def visual_run(run_id, title, scen_name, cfg, initial=None, previous=None, note=""):
    """Ejecución completa cuyo historial (mejor por generación) se exporta al visor."""
    sc = scen(scen_name)
    ev = Evaluator(sc)
    r = run_ga(ev, cfg, initial)
    hist = []
    for h in r.history:
        rep = ev.report(h["best_sats"])
        h = dict(h)
        h["regions"] = [{"status": x["status"], "coverage": x["coverage"]} for x in rep["regions"]]
        h["bad_sats"] = sorted({v["sat"] for v in rep["violations"]}
                               | {v.get("sat2") for v in rep["violations"] if "sat2" in v})
        hist.append(h)
    out = {
        "id": run_id, "title": title, "note": note,
        "scenario": sc.to_dict(),
        "footprint_deg": ev.lam, "region_radius_deg": ev.rho,
        "config": r.config, "evaluations": r.evaluations,
        "initial": {"sats": r.initial_best.sats, "report": ev.report(r.initial_best.sats),
                    "label": "Mejor de la generación 0"},
        "final": {"sats": r.best.sats, "report": ev.report(r.best.sats),
                  "label": "Mejor final"},
        "history": hist,
    }
    if previous is not None:
        out["initial"] = {"sats": previous, "report": ev.report(previous),
                          "label": "Configuración anterior (evaluada con las nuevas condiciones)"}
    return out, r


# ------------------------------------------------------------------ principal

def run_all(seeds=20, workers=None, quick=False):
    t0 = time.time()
    os.makedirs(RES, exist_ok=True)
    base = GAConfig()
    if quick:
        seeds = 4
        base = replace(base, generations=60)
    budget = base.pop_size + (base.generations - 1) * (base.pop_size - base.elitism)
    seed_list = list(range(1, seeds + 1))
    results = {"params": {"ga": base.__dict__, "seeds": seeds, "budget": budget}}
    all_rows = []

    with ProcessPoolExecutor(max_workers=workers) as pool:
        # E1 ------------------------------------------------------------
        print("E1: Etapa 1, AG vs aleatoria ...", flush=True)
        ga1 = list(pool.map(job_ga, [("etapa1", replace(base, strategy="ignorar", seed=s), None)
                                     for s in seed_list]))
        rnd1 = list(pool.map(job_random, [("etapa1", budget, "ignorar", s) for s in seed_list]))
        ev1 = Evaluator(scen("etapa1"))
        ref1 = ev1.report(heuristic_reference(ev1))
        results["E1"] = {"summary": [summarize(ga1, "AG"), summarize(rnd1, "Búsqueda aleatoria")],
                         "reference": ref1, "curve_ga": mean_curve(ga1),
                         "curve_ga_mean_pop": mean_curve(ga1, "mean_curve")}
        all_rows += ga1 + rnd1

        # E2 ------------------------------------------------------------
        print("E2: Etapa 2, estrategias de restricciones ...", flush=True)
        e2 = {}
        for st in STRATEGIES:
            e2[st] = list(pool.map(job_ga, [("etapa2", replace(base, strategy=st, seed=s), None)
                                            for s in seed_list]))
            all_rows += e2[st]
        rnd2 = list(pool.map(job_random, [("etapa2", budget, "deb", s) for s in seed_list]))
        all_rows += rnd2
        ev2 = Evaluator(scen("etapa2"))
        ref2 = ev2.report(heuristic_reference(ev2))
        results["E2"] = {"summary": [summarize(e2[st], "AG + " + st) for st in STRATEGIES]
                         + [summarize(rnd2, "Búsqueda aleatoria (Deb)")],
                         "reference": ref2,
                         "curves": {st: mean_curve(e2[st]) for st in STRATEGIES},
                         "feasible_curves": {st: mean_curve(e2[st], "feasible_curve")
                                             for st in STRATEGIES}}

        # E3 ------------------------------------------------------------
        print("E3: validez de soluciones de Etapa 1 en Etapa 2 ...", flush=True)
        e3 = []
        for r in ga1:
            rep = ev2.report(r["best_sats"])
            e3.append({"seed": r["seed"], "fitness_e1": r["fitness"], "feasible_e2": rep["feasible"],
                       "violation_e2": rep["violation"],
                       "violations": [v["zone"] if v["type"] == "zona" else "separación"
                                      for v in rep["violations"]]})
        results["E3"] = {"rows": e3,
                         "valid_pct": round(100 * sum(x["feasible_e2"] for x in e3) / len(e3), 1)}

        # E4 ------------------------------------------------------------
        print("E4: cambios de condiciones ...", flush=True)
        prev_best = max((r for r in e2["reparacion"]), key=lambda r: r["fitness"])
        prev_ev = Evaluator(scen("etapa2"))
        prev_cfg = replace(base, strategy="reparacion", seed=prev_best["seed"])
        prev_pop = run_ga(prev_ev, prev_cfg, record_positions=False).final_population
        warm_gens = max(10, base.generations // 3)
        e4 = {}
        for ch in CHANGES:
            evc = Evaluator(scen(ch))
            old = evc.report(prev_best["best_sats"])
            cold = list(pool.map(job_ga, [(ch, replace(base, strategy="reparacion", seed=s), None)
                                          for s in seed_list]))
            warm = list(pool.map(job_ga, [(ch, replace(base, strategy="reparacion", seed=s,
                                                       generations=warm_gens), prev_pop)
                                          for s in seed_list]))
            for r in warm:
                r["method"] = "AG-caliente"
            all_rows += cold + warm
            e4[ch] = {"description": scen(ch).description,
                      "old_config": {"fitness": old["fitness"], "feasible": old["feasible"],
                                     "violation": old["violation"], "n_covered": old["n_covered"],
                                     "violations": old["violations"],
                                     "regions": [(x["name"], x["status"]) for x in old["regions"]]},
                      "summary": [summarize(cold, f"En frío ({base.generations} gen)"),
                                  summarize(warm, f"En caliente ({warm_gens} gen)")],
                      "reference": evc.report(heuristic_reference(evc))}
        results["E4"] = e4

        # E5 ------------------------------------------------------------
        print("E5: sensibilidad de parámetros ...", flush=True)
        variants = [
            ("Base (pm=0.2, elit=2, pob=60)", base),
            ("Sin reubicación dirigida", replace(base, targeted_rate=0.0)),
            ("pm=0.05", replace(base, mutation_rate=0.05)),
            ("pm=0.5", replace(base, mutation_rate=0.5)),
            ("Sin elitismo", replace(base, elitism=0)),
            ("Sigma fijo 3°", replace(base, sigma_start=3.0, sigma_end=3.0)),
            ("pob=20 (más gen.)", replace(base, pop_size=20,
                                         generations=1 + (budget - 20) // 18)),
            ("pob=120 (menos gen.)", replace(base, pop_size=120,
                                            generations=1 + (budget - 120) // 118)),
        ]
        e5 = []
        for label, cfg in variants:
            rows = list(pool.map(job_ga, [("etapa2", replace(cfg, strategy="reparacion", seed=s), None)
                                          for s in seed_list]))
            e5.append(summarize(rows, label))
        results["E5"] = e5

    # ------------------------------------------------------------ visor
    print("Ejecuciones para el visor 3D ...", flush=True)
    runs = []
    v1, _ = visual_run("etapa1", "Etapa 1 · sin restricciones", "etapa1",
                       replace(base, strategy="ignorar", seed=1))
    runs.append(v1)
    v2i, _ = visual_run("etapa2_ignorar", "Etapa 2 · ignorando restricciones (contraejemplo)",
                        "etapa2", replace(base, strategy="ignorar", seed=1),
                        note="El AG no considera las restricciones: el resultado puede invadir zonas.")
    runs.append(v2i)
    v2, _ = visual_run("etapa2", "Etapa 2 · con restricciones (reparación + Deb)", "etapa2",
                       replace(prev_cfg))
    runs.append(v2)
    for ch in CHANGES:
        vc, _ = visual_run(ch, "Cambio · " + scen(ch).description.split(": ", 1)[-1], ch,
                           replace(base, strategy="reparacion", seed=1, generations=warm_gens),
                           initial=prev_pop, previous=v2["final"]["sats"],
                           note="Re-optimización en caliente a partir de la población de la Etapa 2.")
        runs.append(vc)
    results["elapsed_s"] = round(time.time() - t0, 1)

    # ------------------------------------------------------------ archivos
    with open(os.path.join(RES, "experimentos.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    with open(os.path.join(RES, "corridas.csv"), "w", newline="", encoding="utf-8") as f:
        cols = ["scenario", "method", "seed", "fitness", "feasible", "violation", "n_covered",
                "weighted_coverage", "evaluations", "gen_reach_090"]
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    with open(os.path.join(RES, "resumen.md"), "w", encoding="utf-8") as f:
        f.write(markdown_summary(results))
    with open(os.path.join(VIEW, "data.js"), "w", encoding="utf-8") as f:
        f.write("// Generado por `python main.py experiments`. No editar a mano.\n")
        f.write("window.ASTRO_DATA = ")
        json.dump({"runs": runs, "experiments": results,
                   "generated": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)
        f.write(";\n")
    print(f"Listo en {results['elapsed_s']} s. Ver results/resumen.md y viewer/index.html")
    return results


# ------------------------------------------------------------------ reporte

def _table(rows):
    head = "| Método | Corridas | Aptitud media ± desv. | Mín | Máx | % factibles | Regiones cubiertas (media) | Gen. para 0.90 |\n"
    head += "|---|---|---|---|---|---|---|---|\n"
    for s in rows:
        g90 = "-" if s["gen_reach_090_mean"] is None else f"{s['gen_reach_090_mean']} ({s['reach_090_pct']}%)"
        head += (f"| {s['label']} | {s['runs']} | {s['fitness_mean']} ± {s['fitness_std'] if s['fitness_std'] >= 0.0001 else '< 0.0001'} | "
                 f"{s['fitness_min']} | {s['fitness_max']} | {s['feasible_pct']} | "
                 f"{s['covered_mean']} | {g90} |\n")
    return head


def markdown_summary(r):
    p = r["params"]
    out = ["# Resultados de los experimentos\n",
           f"Semillas por configuración: {p['seeds']}. Presupuesto por corrida: "
           f"{p['budget']} evaluaciones. Tiempo total: {r['elapsed_s']} s.\n",
           "Aptitud máxima teórica en la Etapa 1 y 2 (satélite en el centro de cada región "
           "y los 2 sobrantes en las regiones Alta): ver fila *Referencia*.\n",
           "## E1 · Etapa 1 (sin restricciones)\n", _table(r["E1"]["summary"]),
           f"\nReferencia construida a mano: aptitud {r['E1']['reference']['fitness']}.\n",
           "## E2 · Etapa 2 (con restricciones)\n", _table(r["E2"]["summary"]),
           f"\nReferencia construida a mano: aptitud {r['E2']['reference']['fitness']}, "
           f"factible: {r['E2']['reference']['feasible']}.\n",
           "## E3 · ¿Las soluciones de la Etapa 1 siguen siendo válidas en la Etapa 2?\n",
           f"Válidas: {r['E3']['valid_pct']}% de las {len(r['E3']['rows'])} soluciones.\n"]
    bad = [x for x in r["E3"]["rows"] if not x["feasible_e2"]]
    if bad:
        out.append("\n| Semilla | Violación (grados) | Causas |\n|---|---|---|\n")
        for x in bad:
            out.append(f"| {x['seed']} | {x['violation_e2']} | {', '.join(sorted(set(x['violations'])))} |\n")
    out.append("\n## E4 · Cambios de condiciones\n")
    for ch, d in r["E4"].items():
        o = d["old_config"]
        out.append(f"\n### {ch}\n{d['description']}\n\n")
        out.append(f"Configuración anterior bajo las nuevas condiciones: aptitud {o['fitness']}, "
                   f"factible: {o['feasible']}, violación {o['violation']}°, "
                   f"regiones cubiertas {o['n_covered']}.\n")
        if o["violations"]:
            out.append("Incumple: " + "; ".join(
                f"satélite {v['sat']} en {v.get('zone', 'separación')} ({v['depth_deg']}°)"
                for v in o["violations"]) + "\n")
        out.append("\n" + _table(d["summary"]))
        out.append(f"\nReferencia construida a mano: aptitud {d['reference']['fitness']}.\n")
    out.append("\n## E5 · Sensibilidad de parámetros (Etapa 2, reparación)\n")
    out.append(_table(r["E5"]))
    return "".join(out)
