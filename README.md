# AstroShield-KARA

Proyecto educativo que utiliza un **algoritmo genético** para distribuir **8 satélites** y observar seis regiones terrestres con distintas prioridades. Considera desechos espaciales, posiciones ocupadas y separación entre satélites, y muestra las ejecuciones guardadas en un **globo 3D con Three.js**.

## Requisitos e inicio rápido

- Python 3.10 o posterior recomendado; los módulos utilizan la biblioteca estándar.
- Git para clonar el repositorio.
- Navegador con WebGL y conexión a internet para cargar Three.js y OrbitControls.

```bash
git clone https://github.com/HembiUnU/AstroShield-KARA.git
cd AstroShield-KARA
python -m http.server 8000 --bind 127.0.0.1
```

Abre [http://localhost:8000/viewer/](http://localhost:8000/viewer/). Si ya clonaste el repositorio, ejecuta solamente el último comando desde su raíz. Detén el servidor con `Ctrl+C`.

El visor permite girar el globo, acercarse, seleccionar ejecuciones, comparar **Inicial / Final**, recorrer generaciones y consultar cobertura, restricciones y experimentos.

**El visor lee resultados guardados en `viewer/data.js`; no ejecuta una nueva optimización.** Cambiar un escenario JSON no actualiza automáticamente la visualización.

## Estructura

| Ruta | Contenido |
|---|---|
| `astroshield/geometry.py` | Geometría esférica, distancias, huellas y muestreo |
| `astroshield/scenario.py` | Representación y carga de escenarios JSON |
| `astroshield/evaluation.py` | Cobertura, aptitud y restricciones |
| `astroshield/ga.py` | Algoritmo genético, búsqueda aleatoria y referencia heurística |
| `scenarios/` | Etapas 1 y 2 y cambios de condiciones |
| `test/test_astroshield.py` | Pruebas automáticas |
| `viewer/` | Visor 3D, textura terrestre y datos de ejecuciones |

## Ejecutar una nueva búsqueda

Desde la raíz del proyecto, inicia `python` y pega:

```python
from pprint import pprint
from astroshield.scenario import load_scenario
from astroshield.evaluation import Evaluator
from astroshield.ga import GAConfig, run_ga

scenario = load_scenario("scenarios/etapa2.json")
evaluator = Evaluator(scenario)
config = GAConfig(pop_size=60, generations=150, strategy="reparacion", seed=1)
result = run_ga(evaluator, config)

pprint(result.best.sats)
pprint(evaluator.report(result.best.sats))
pprint([result.history[0], result.history[-1]])
```

El reporte incluye aptitud, cobertura ponderada, factibilidad, violación total y estado de cada región. El historial permite analizar la evolución. Cambia la ruta del escenario, los parámetros o la semilla para comparar ejecuciones.

**Exportación pendiente:** la cabecera de `viewer/data.js` menciona `python main.py experiments`, pero `main.py` no está incluido en esta versión. El ejemplo anterior muestra resultados en consola; no regenera los datos del visor. Tampoco se incluyen `astroshield/experiments.py` ni una carpeta `results/`.

## Modelo y decisiones de diseño

### Representación y cobertura

Cada individuo contiene ocho pares `(latitud, longitud)`, uno por satélite. Se evalúa la constelación completa sobre una Tierra esférica de radio **6371 km**, con posiciones estáticas a **500 km de altitud** y elevación mínima de observación de **30°**.

| Región | Centro: latitud, longitud | Prioridad inicial |
|---|---|---|
| Península de Yucatán | 20.5°, -89.0° | Alta |
| Amazonía brasileña | -3.5°, -62.0° | Alta |
| California | 36.8°, -119.4° | Media |
| Sahel | 15.0°, 0.0° | Media |
| Japón | 36.0°, 138.0° | Media |
| Interior de Australia | -25.0°, 133.0° | Normal |

Cada región es un disco de **300 km de radio**, representado por **37 muestras**. La huella del satélite se calcula con la altitud y la elevación mínima; su semiángulo es aproximadamente **6.58°**.

- **Cobertura:** fracción de muestras observadas por al menos un satélite.
- **Redundancia:** fracción observada por dos o más satélites.
- **Cubierta:** cobertura ≥ 95 %; con 37 muestras se requieren al menos 36.
- **Parcial:** cobertura mayor que cero e inferior al 95 %.
- **No cubierta:** ninguna muestra observada.

### Aptitud y prioridades

Las prioridades tienen pesos **Alta = 3, Media = 2 y Normal = 1**. La evaluación utiliza promedios ponderados por esos pesos:

```text
F = 0.85 × cobertura + 0.10 × redundancia + 0.05 × proximidad
proximidad por región = max(0, 1 - d / 90)
```

`d` es la distancia angular, en grados, entre el centro de la región y el satélite más cercano. La cobertura es el objetivo principal; la redundancia favorece aprovechar los satélites sobrantes y la proximidad orienta la búsqueda cuando todavía no se cubren regiones.

### Restricciones y validez

La etapa 2 incorpora las siguientes zonas de exclusión:

| Zona u objeto | Centro: latitud, longitud | Radio angular |
|---|---|---:|
| Atlántico Norte | 45°, -35° | 12° |
| Pacífico Sur | -30°, -120° | 10° |
| Región polar norte | 78°, 30° | 8° |
| Objeto A | 10°, 45° | 5° |
| Objeto B | -15°, 110° | 5° |

Además, exige una separación mínima de **3°** entre satélites propios. La violación total suma las invasiones de zonas y los déficits de separación, en grados. Se considera factible si esa suma es ≤ `1e-9`, como tolerancia numérica.

**Una aptitud alta no garantiza una configuración válida.** En el escenario base se busca cubrir las seis regiones respetando las restricciones y mejorar la aptitud frente a la población inicial y los métodos de referencia. Este objetivo no es una prueba de optimalidad ni un criterio automático de parada.

## Algoritmo genético y parámetros

El proceso genera posiciones aleatorias uniformes en área, evalúa configuraciones, selecciona padres por torneo y aplica cruce alineando satélites cercanos. Después modifica posiciones mediante desplazamientos, reubicación aleatoria o reubicación dirigida hacia regiones. Conserva élites y registra cada generación.

| Parámetro | Valor predeterminado | Propósito |
|---|---:|---|
| Población | 60 | Mantener alternativas de búsqueda |
| Generaciones | 150, incluida la generación 0 | Limitar el proceso y registrar su evolución |
| Torneo | 3 individuos | Seleccionar padres con presión moderada |
| Probabilidad de cruce | 0.9 | Combinar configuraciones |
| Probabilidad de desplazamiento por satélite | 0.2 | Explorar posiciones cercanas |
| Escala del desplazamiento | 12° → 0.5° | Explorar al inicio y ajustar al final |
| Reubicación aleatoria / dirigida | 0.02 / 0.02 | Introducir saltos y alcanzar regiones distantes |
| Elitismo | 2 | Conservar individuos de mejor calidad |
| Semilla | 1 | Repetir una ejecución bajo el mismo entorno |

Estos valores son configurables mediante `GAConfig`. Son valores iniciales de trabajo, no parámetros universalmente óptimos. Los experimentos guardados comparan variantes para observar su efecto.

Se incluyen cuatro tratamientos de restricciones: `ignorar`, que ordena solo por aptitud; `penalizacion`, que resta `0.05 × violación`; `deb`, que prefiere factibles y compara infactibles por menor violación; y **`reparacion`**, la opción predeterminada, que desplaza posiciones conflictivas y aplica las reglas de Deb. La reparación tiene iteraciones limitadas, por lo que se verifica siempre la factibilidad final.

## Escenarios y cambios de condiciones

| Archivo en `scenarios/` | Condición |
|---|---|
| `etapa1.json` | Sin zonas prohibidas ni separación mínima |
| `etapa2.json` | Tres zonas de desechos, dos objetos y separación mínima |
| `cambio_golfo.json` | Nueva zona en (23°, -90°), de radio 5.5° |
| `cambio_prioridades.json` | Australia pasa a Alta y Yucatán a Media |
| `cambio_japon.json` | Nueva zona en (37°, 136°), de radio 10° |

Los cambios se representan con archivos JSON. Una configuración anterior debe reevaluarse con las nuevas condiciones: puede conservar cobertura y volverse inválida, o seguir siendo válida y perder calidad relativa por el cambio de prioridades.

## Pruebas, resultados e interpretación

Desde la raíz del repositorio:

```bash
python -m unittest discover -s ./test -p "test_astroshield.py" -v
```

La carpeta es **`test`**, en singular. La suite contiene **18 pruebas** de geometría, cobertura, prioridades, detección de restricciones, reparación, reproducibilidad, evolución y comparación con búsqueda aleatoria.

Las cifras siguientes proceden de `viewer/data.js`, cuyo campo `generated` indica `2026-10-23 19:09:32`. Son registros guardados, no una nueva ejecución del visor. Las ejecuciones base mostradas usan semilla 1 y 150 generaciones; los tres cambios usan 50 generaciones y parten de una búsqueda previa.

| Caso | Aptitud final | Regiones cubiertas | Factible |
|---|---:|---:|---|
| Etapa 1 | 0.94602 | 6 de 6 | Sí |
| Etapa 2, ignorando restricciones | 0.94602 | 6 de 6 | No |
| Etapa 2, reparación | 0.94608 | 6 de 6 | Sí |
| Nueva zona del Golfo | 0.94548 | 6 de 6 | Sí |
| Cambio de prioridades | 0.94251 | 6 de 6 | Sí |
| Nueva zona sobre Japón | 0.83934 | 5 de 6 | Sí |

### Evidencias de los casos requeridos

| Prueba y condiciones | Resultado registrado e interpretación |
|---|---|
| Escenario inicial: etapa 1 | Cubre las seis regiones; muestra que la búsqueda encuentra configuraciones útiles sin restricciones espaciales. |
| Evolución: etapa 2 con reparación | La mejor aptitud pasa de 0.22985 a 0.94608. El historial permite seguir la mejora, sin demostrar por ello optimalidad global. |
| Tres zonas de desechos: etapa 2 | La solución final tiene violación cero. La prueba automática de invasión del Atlántico Norte verifica detección explícita; los cambios del Golfo y Japón evalúan restricciones cercanas a regiones de interés. |
| Dos posiciones ocupadas: etapa 2 | La solución final tiene violación cero, incluyendo exclusiones de A y B. Hay una prueba directa de invasión del Objeto A; no una equivalente específica para B. |
| Espacio reducido: nueva zona del Golfo | La configuración anterior invade la nueva zona. La adaptación termina factible y conserva seis regiones cubiertas, con una pequeña reducción de aptitud. |
| Condición difícil: zona sobre Japón | Termina factible con cinco regiones cubiertas y Japón al 18.92 % de cobertura. Es el resultado encontrado, no una demostración de imposibilidad para todas las configuraciones. |
| Variación: 20 ejecuciones por método en etapa 2 | Con reparación, la aptitud final va de 0.9459 a 0.9461, según el resumen redondeado; el 100 % de esas soluciones finales es factible. La consistencia observada se limita a los casos registrados. |
| Prueba propia: quitar reubicación dirigida | En `experiments.E5`, la aptitud media baja de 0.9460 a 0.9387 y la primera generación que alcanza 0.90 pasa, en promedio, de 11.5 a 42.5. Esto respalda la utilidad del operador en los experimentos incluidos. |

En `experiments.E2`, la búsqueda aleatoria con Deb obtiene aptitud media **0.4627**, frente a **0.9460** del algoritmo con reparación. Ignorar restricciones alcanza una aptitud media similar a la del algoritmo con reparación, pero solo el **20 %** de sus soluciones finales es factible. Por eso se comparan tanto calidad como validez, además de la cobertura por región.

Las tablas y curvas completas están guardadas en el bloque `experiments` de `viewer/data.js` y se consultan desde el visor. Una solución heurística incluida en el código sirve como **referencia construida a mano**; no constituye un óptimo global demostrado.

## Limitaciones

- El modelo es educativo y estático: no calcula órbitas, tiempos de revisita ni cobertura temporal.
- La cobertura se estima con 37 puntos por región y depende de los pesos y umbrales elegidos.
- La redundancia mide observación compartida de muestras; no garantiza tolerancia total ante cualquier falla.
- Las zonas y los objetos del escenario base quedan lejos de las regiones, por lo que no demuestran por sí solos competencia entre restricciones y cobertura.
- El algoritmo es estocástico: estancarse o no cubrir una región no demuestra que sea imposible mejorar.
- La exportación de nuevas ejecuciones al visor no es reproducible con los archivos actualmente incluidos, porque falta el generador mencionado en `data.js`.

## Uso de inteligencia artificial

Según el registro de desarrollo del equipo, **Claude mediante Claude Code** generó la mayor parte del modelo, código, experimentos y documentación original. **ChatGPT/Codex** ayudó a revisar y redactar este README y a explicar el flujo de Git y GitHub.

Para esta documentación se contrastaron los comandos, rutas, parámetros y resultados con los archivos disponibles. También se comprobó una ejecución del escenario base, que produjo ocho satélites, seis regiones cubiertas y violación cero. Estas verificaciones no equivalen a reproducir todos los experimentos guardados ni confirman por sí solas las acciones atribuidas al desarrollo original.

El equipo debe respaldar con evidencia las verificaciones que declare haber realizado y explicar las decisiones del sistema durante la presentación. Las aportaciones se consultan en el [historial de commits](https://github.com/HembiUnU/AstroShield-KARA/commits/main/).
