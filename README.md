# AstroShield-KARA

Sistema educativo que utiliza un **algoritmo genético** para distribuir **8 satélites** y observar seis regiones terrestres, considerando prioridades, desechos espaciales y posiciones ocupadas. Incluye un visor de la constelación en **3D con Three.js**.

## Requisitos

- Python 3.10 o posterior recomendado.
- Git para clonar el repositorio.
- Navegador con WebGL y conexión a internet para cargar las bibliotecas del visor.

El algoritmo y las pruebas utilizan la biblioteca estándar de Python; no requieren instalar paquetes adicionales.

## Abrir el visor 3D

Desde una terminal:

```bash
git clone https://github.com/HembiUnU/AstroShield-KARA.git
cd AstroShield-KARA
python -m http.server 8000 --bind 127.0.0.1
```

Si ya tienes el repositorio, ejecuta solamente el último comando desde su carpeta raíz. Abre [http://localhost:8000/viewer/](http://localhost:8000/viewer/) y usa `Ctrl+C` para detener el servidor.

El visor permite girar el globo, acercarse, seleccionar escenarios, reproducir generaciones y comparar la configuración inicial con la final.

**El visor muestra ejecuciones guardadas en [viewer/data.js](viewer/data.js); no ejecuta nuevamente el algoritmo.**

## Ejecutar el algoritmo

Desde la raíz del proyecto, inicia `python` y pega:

```python
from pprint import pprint
from astroshield.scenario import load_scenario
from astroshield.evaluation import Evaluator
from astroshield.ga import GAConfig, run_ga

scenario = load_scenario("scenarios/etapa2.json")
evaluator = Evaluator(scenario)
result = run_ga(evaluator, GAConfig(generations=150, seed=1))
pprint(result.best.sats)
pprint(evaluator.report(result.best.sats))
```

Puedes cambiar el escenario, las generaciones o la semilla. El reporte muestra aptitud, cobertura, factibilidad y violaciones.

**Pendiente:** `data.js` menciona un generador `main.py` que no está incluido en el repositorio. El ejemplo anterior produce resultados en consola y no actualiza el visor.

## Cómo funciona

Cada solución contiene ocho posiciones `(latitud, longitud)`. El algoritmo usa selección por torneo, cruce, mutación, reubicación dirigida y elitismo. Por defecto trabaja con **60 individuos, 150 generaciones y reparación de restricciones**.

Las regiones son Yucatán, Amazonía, California, Sahel, Japón y el interior de Australia. Cada una tiene un radio de **300 km** y se considera cubierta si se observa al menos el **95 % de sus 37 muestras**. Los escenarios usan una altitud de 500 km y elevación mínima de 30°.

La aptitud combina promedios ponderados por prioridad:

```text
Aptitud = 0.85 × cobertura + 0.10 × redundancia + 0.05 × proximidad
```

Las prioridades tienen pesos Alta = 3, Media = 2 y Normal = 1. La redundancia mide observación por dos o más satélites; la proximidad favorece acercarse a las regiones.

En la etapa 2 se evitan tres zonas de desechos y dos objetos existentes, además de exigir una separación mínima de 3° entre satélites. Se incluyen las estrategias `ignorar`, `penalizacion`, `deb` y `reparacion`. **Una aptitud alta no garantiza que la configuración sea válida.**

## Organización y escenarios

| Carpeta | Contenido |
|---|---|
| [astroshield/](astroshield/) | Algoritmo, evaluación, geometría y carga de escenarios |
| [scenarios/](scenarios/) | Etapas 1 y 2; cambios en el Golfo, Japón y prioridades |
| [test/](test/) | Pruebas automáticas |
| [viewer/](viewer/) | Globo 3D, recursos y ejecuciones guardadas |

Los escenarios JSON permiten modificar las condiciones sin cambiar el algoritmo. Una configuración anterior debe reevaluarse cuando se agregan restricciones o cambian prioridades.

## Pruebas y resultados

Ejecuta desde la raíz:

```bash
python -m unittest discover -s test -v
```

Las pruebas cubren geometría, cobertura, restricciones, reparación, reproducibilidad y comparación con búsqueda aleatoria.

Resultados de las ejecuciones guardadas en `viewer/data.js` (semilla 1):

| Ejecución | Aptitud final | Regiones cubiertas | Factible |
|---|---:|---:|---|
| Etapa 1 | 0.94602 | 6 de 6 | Sí |
| Etapa 2, ignorando restricciones | 0.94602 | 6 de 6 | No |
| Etapa 2, con reparación | 0.94608 | 6 de 6 | Sí |
| Cambio del Golfo | 0.94548 | 6 de 6 | Sí |
| Cambio de prioridades | 0.94251 | 6 de 6 | Sí |
| Cambio sobre Japón | 0.83934 | 5 de 6 | Sí |

Las ejecuciones base usan 150 generaciones; las de cambio usan 50 y parten de una búsqueda previa. En la etapa 2 con reparación, la aptitud aumenta de **0.22985 a 0.94608**. En el caso de Japón, el resultado conserva cobertura parcial de esa región y respeta las restricciones.

Los experimentos guardados también comparan 20 ejecuciones por método y variantes de parámetros. Estos resultados describen los casos registrados y no garantizan el mismo comportamiento en cualquier escenario.

## Limitaciones y uso de IA

El modelo es estático, aproxima la Tierra mediante una esfera y estima la cobertura por muestreo. No calcula órbitas reales ni cobertura a lo largo del tiempo, y el algoritmo no garantiza encontrar el óptimo global.

Este README se redactó con asistencia de IA y se contrastó con el código y los datos del repositorio. El equipo debe completar cualquier otro uso de IA y las verificaciones realizadas antes de entregar, las aportaciones se pueden consultar en el historil de commits
