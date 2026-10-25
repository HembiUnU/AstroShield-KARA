"""Pruebas automáticas. Ejecutar con:  python -m unittest discover -s tests -v"""
import math
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from astroshield import geometry as g
from astroshield.scenario import load_scenario
from astroshield.evaluation import Evaluator
from astroshield.ga import GA, GAConfig, run_ga, random_search, heuristic_reference


def S(name):
    return load_scenario(os.path.join(ROOT, "scenarios", name + ".json"))


class TestGeometry(unittest.TestCase):
    def test_distancia_conocida(self):
        # Ecuador: 90° de longitud = 90° angulares; polo a ecuador = 90°
        self.assertAlmostEqual(g.ang_dist(0, 0, 0, 90), 90.0, places=6)
        self.assertAlmostEqual(g.ang_dist(90, 0, 0, 123), 90.0, places=6)
        # Cruce del antimeridiano: 179° y -179° están a 2°
        self.assertAlmostEqual(g.ang_dist(0, 179, 0, -179), 2.0, places=6)

    def test_destino_y_rumbo_consistentes(self):
        rng = random.Random(0)
        for _ in range(200):
            lat, lon = g.random_point(rng)
            b, d = rng.uniform(0, 360), rng.uniform(0.1, 30)
            p = g.destination(lat, lon, b, d)
            self.assertAlmostEqual(g.ang_dist(lat, lon, *p), d, places=5)

    def test_huella(self):
        # 500 km, elevación mínima 30° -> ~6.58° (~730 km)
        lam = g.footprint_half_angle(500, 30)
        self.assertAlmostEqual(lam, 6.582, places=2)
        # a mayor altitud, mayor huella; a mayor elevación mínima, menor huella
        self.assertGreater(g.footprint_half_angle(800, 30), lam)
        self.assertLess(g.footprint_half_angle(500, 45), lam)

    def test_muestras_dentro_del_disco(self):
        pts = g.disk_samples(20.5, -89.0, 2.7, 37)
        self.assertEqual(len(pts), 37)
        for p in pts:
            self.assertLessEqual(g.ang_dist(20.5, -89.0, *p), 2.7 + 1e-9)


class TestEvaluacion(unittest.TestCase):
    def setUp(self):
        self.ev = Evaluator(S("etapa2"))

    def test_satelite_en_el_centro_cubre_la_region(self):
        r = self.ev.sc.regions[0]
        rep = self.ev.report([(r.lat, r.lon)] + [(-80 + i, 0) for i in range(7)])
        self.assertEqual(rep["regions"][0]["status"], "cubierta")
        self.assertEqual(rep["regions"][0]["coverage"], 1.0)

    def test_satelite_lejano_no_cubre(self):
        rep = self.ev.report([(-60, -150 + 5 * i) for i in range(8)])
        self.assertTrue(all(r["status"] == "no cubierta" for r in rep["regions"]))
        self.assertEqual(rep["weighted_coverage"], 0.0)

    def test_cobertura_parcial(self):
        r = self.ev.sc.regions[0]
        # a lambda de distancia del centro sólo se ve aprox. la mitad del disco
        p = g.destination(r.lat, r.lon, 0, self.ev.lam)
        rep = self.ev.report([p] + [(-80 + i, 0) for i in range(7)])
        self.assertEqual(rep["regions"][0]["status"], "parcial")

    def test_restriccion_zona_detectada(self):
        z = self.ev.sc.zones[0]  # Atlántico Norte
        sats = heuristic_reference(self.ev)
        self.assertTrue(self.ev.report(sats)["feasible"])
        sats[7] = (z.lat, z.lon)
        rep = self.ev.report(sats)
        self.assertFalse(rep["feasible"])
        self.assertTrue(any(v.get("zone") == z.name for v in rep["violations"]))

    def test_objetos_ocupados_detectados(self):
        sats = heuristic_reference(self.ev)
        sats[7] = (10.0, 45.0)  # Objeto A
        rep = self.ev.report(sats)
        self.assertFalse(rep["feasible"])
        self.assertEqual(rep["violations"][0]["kind"], "objeto")

    def test_separacion_minima(self):
        sats = heuristic_reference(self.ev)
        sats[7] = sats[6]
        self.assertFalse(self.ev.report(sats)["feasible"])

    def test_prioridad_cambia_la_aptitud(self):
        # Cubrir sólo Australia vale más cuando Australia es prioridad Alta
        far = [(-80 + 2 * i, 0) for i in range(7)]
        sats = [(-25.0, 133.0)] + far
        f_old = Evaluator(S("etapa2")).report(sats)["fitness"]
        f_new = Evaluator(S("cambio_prioridades")).report(sats)["fitness"]
        self.assertGreater(f_new, f_old)


class TestAlgoritmo(unittest.TestCase):
    def test_reproducible_con_semilla(self):
        ev = Evaluator(S("etapa2"))
        cfg = GAConfig(generations=15, seed=7)
        a = run_ga(ev, cfg, record_positions=False)
        b = run_ga(ev, cfg, record_positions=False)
        self.assertEqual(a.best.sats, b.best.sats)

    def test_mejor_nunca_empeora(self):
        ev = Evaluator(S("etapa2"))
        r = run_ga(ev, GAConfig(generations=40, seed=3, strategy="deb"))
        keys = [((1, h["best_fitness"]) if h["best_violation"] == 0 else (0, -h["best_violation"]))
                for h in r.history]
        self.assertEqual(keys, sorted(keys))

    def test_reparacion_produce_factibles(self):
        ev = Evaluator(S("cambio_golfo"))
        ga = GA(ev, GAConfig(seed=1))
        for _ in range(50):
            fixed = ga.repair(ga.random_config())
            self.assertEqual(ev.violation(fixed)[0], 0.0)

    def test_resultado_final_respeta_restricciones(self):
        for st in ("deb", "reparacion", "penalizacion"):
            ev = Evaluator(S("etapa2"))
            r = run_ga(ev, GAConfig(generations=60, seed=2, strategy=st), record_positions=False)
            self.assertTrue(ev.report(r.best.sats)["feasible"], st)

    def test_ag_supera_busqueda_aleatoria(self):
        ev = Evaluator(S("etapa2"))
        for seed in (1, 2, 3):
            r = run_ga(ev, GAConfig(generations=80, seed=seed), record_positions=False)
            rnd = random_search(ev, r.evaluations, seed=seed)
            self.assertGreater(r.best.fitness, rnd.fitness + 0.2)

    def test_ag_cubre_todas_las_regiones(self):
        ev = Evaluator(S("etapa2"))
        r = run_ga(ev, GAConfig(seed=1), record_positions=False)
        self.assertEqual(ev.report(r.best.sats)["n_covered"], 6)

    def test_cambio_invalida_configuracion_anterior(self):
        ev2 = Evaluator(S("etapa2"))
        r = run_ga(ev2, GAConfig(seed=1), record_positions=False)
        # el centro de Yucatán queda dentro de la nueva zona del Golfo
        rep = Evaluator(S("cambio_golfo")).report(r.best.sats)
        self.assertFalse(rep["feasible"])


if __name__ == "__main__":
    unittest.main()
