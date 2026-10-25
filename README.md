# AstroShield · Evolucionar una constelación inteligente

Proyecto educativo que usa un **algoritmo genético** para colocar **8 satélites** sobre **6 regiones** con distintas prioridades, respetando zonas de desechos, posiciones ocupadas y una separación mínima. El resultado se muestra en un **globo 3D** (Three.js) construido con los datos reales de cada ejecución.

**Grupo:** LITTID72

**Integrantes:**
* Angeles García ROberto Pablo
* Cortez Vargas Kristopher Eiael
* Morales Millan Jade Alejandro
* Navarro Galván José Antonio

## Inicio rápido

Requiere **Python 3.10+** (sólo biblioteca estándar) y un navegador con WebGL e internet (Three.js se carga desde una CDN).

```bash
git clone https://github.com/HembiUnU/AstroShield-KARA.git
cd AstroShield-KARA

python -m http.server 8000 --bind 127.0.0.1   # visor: abrir http://localhost:8000/viewer/
python -m unittest discover -s test -v         # 18 pruebas automáticas

python main.py experiments            # E1-E5 (≈ 7 min); regenera results/ y viewer/data.js
python main.py experiments --quick    # versión corta (≈ 30 s)
python main.py run --scenario etapa2 --strategy reparacion --seed 3 --out results/mi_corrida.json
python main.py evaluate --scenario cambio_golfo --config results/mi_corrida.json
```

`run` también admite `--generations` y `--pop`. El visor **lee los resultados guardados en `viewer/data.js`**; no ejecuta una nueva optimización.

| Ruta | Contenido |
|---|---|
| `main.py` | Línea de comandos: `experiments`, `run`, `evaluate` |
| `astroshield/` | `geometry.py` (geometría esférica), `scenario.py` (carga y validación de escenarios), `evaluation.py` (cobertura, aptitud y restricciones), `ga.py` (algoritmo genético), `experiments.py` (E1–E5 y exportación al visor) |
| `scenarios/` | Etapa 1, Etapa 2 y tres cambios de condiciones (JSON) |
| `test/` | Pruebas automáticas |
| `results/` | Resultados de los experimentos: `resumen.md`, `experimentos.json`, `corridas.csv` |
| `viewer/` | Visor 3D, textura de la Tierra y `data.js` |

---

## 1. Definición del problema

### 1.1 Modelo espacial
* Tierra esférica de radio 6371 km. Los satélites ocupan **posiciones fijas** a **500 km** de altitud (no se simula el movimiento orbital, lo cual el enunciado permite).
* **Huella:** un punto del suelo se observa si ve al satélite con al menos **30° de elevación**. Semiángulo: λ = arccos(R·cos ε / (R + h)) − ε ≈ **6.58° (732 km)**.
* **Regiones:** discos de **300 km (2.70°)**, representados con **37 puntos** repartidos uniformemente en área.
* **Zonas y objetos:** un satélite los invade si su distancia angular al centro es menor que el radio. Ambos tipos se tratan igual.
* **Separación mínima** (decisión del equipo, Etapa 2): **3°** (~330 km) entre satélites propios.

| Región | Centro | Prioridad | | Zona u objeto | Centro | Radio |
|---|---|---|---|---|---|---|
| Yucatán | 20.5°, −89.0° | Alta | | Atlántico Norte | 45°, −35° | 12° |
| Amazonía | −3.5°, −62.0° | Alta | | Pacífico Sur | −30°, −120° | 10° |
| California | 36.8°, −119.4° | Media | | Polar norte | 78°, 30° | 8° |
| Sahel | 15.0°, 0.0° | Media | | Objeto A | 10°, 45° | 5° |
| Japón | 36.0°, 138.0° | Media | | Objeto B | −15°, 110° | 5° |
| Australia | −25.0°, 133.0° | Normal | | | | |

### 1.2 Representación y cobertura
* Un individuo es una lista de **8 genes**, cada uno la posición (lat, lon) de un satélite. Toda la constelación se evalúa completa.
* `cobertura(r)` = fracción de los 37 puntos vistos por ≥ 1 satélite; `redundancia(r)` = fracción vista por ≥ 2.
* Región **cubierta** si cobertura ≥ 95 % (36 de 37 puntos), **parcial** si es mayor que 0, **no cubierta** si es 0.

### 1.3 Aptitud y prioridades
Pesos **Alta = 3, Media = 2, Normal = 1** (W = 13):
```
F = 0.85 · Σ w·cobertura / W  +  0.10 · Σ w·redundancia / W  +  0.05 · Σ w·proximidad / W
proximidad = max(0, 1 − d / 90°),  d = distancia del satélite más cercano al centro de la región
```
* Ningún par de regiones cabe en una huella, así que lo ideal es **un satélite por región** y los **2 sobrantes** en las regiones Alta, que es lo que premia la redundancia.
* La cobertura es escalonada; la proximidad (5 %) da una pendiente que guía la búsqueda sin dominar el objetivo.
* Mejor aptitud conocida: **0.9462**, de una solución construida a mano que se usa como referencia.

### 1.4 Validez
Violación = grados que cada satélite penetra en una zona + déficit de separación entre pares. **Factible ⇔ violación = 0.** Una configuración inválida se rechaza aunque tenga más aptitud. Se compararon cuatro estrategias:

| Estrategia | Qué pasa con una configuración inválida |
|---|---|
| `ignorar` | Nada; sólo como contraejemplo |
| `penalizacion` | Aptitud − 0.05 × violación |
| `deb` | Una factible siempre gana; entre infactibles, la de menor violación |
| `reparacion` (**elegida**) | Se empuja cada satélite al borde de la zona y se separan pares cercanos; luego reglas de Deb |

El resultado final siempre se vuelve a verificar con el evaluador.

### 1.5 Algoritmo y parámetros
| Componente | Valor | Motivo |
|---|---|---|
| Población inicial | 60, uniforme en área | No sesga hacia polos ni regiones |
| Selección | Torneo, k = 3 | Presión moderada |
| Cruce | p = 0.9, **alineado**: empareja cada satélite con el más cercano del otro padre | El orden de los genes es arbitrario; evita heredar dos satélites para la misma región |
| Mutación | p = 0.2 por satélite, desplazamiento \|N(0, σ)\| con σ de 12° a 0.5°; reubicación al azar p = 0.02 | Explorar al inicio, ajustar al final |
| Reubicación dirigida | p = 0.02: salto a una región al azar | Los satélites sobrantes se quedaban en regiones Media (óptimo local) |
| Elitismo | 2 | El mejor nunca se pierde |
| Parada | 150 generaciones (8 702 evaluaciones) | Se estabiliza antes |

Los valores parten de los habituales en algoritmos genéticos; la reubicación dirigida se agregó tras observar el óptimo local. Todos son configurables y el experimento E5 mide su efecto.

### 1.6 Cambios de condiciones
Cada cambio es un JSON nuevo. El sistema evalúa si la configuración anterior **sigue siendo válida** y re-optimiza en frío (150 generaciones) y en caliente (desde la población anterior, 50 generaciones).

| Escenario | Cambio |
|---|---|
| `cambio_golfo` | Zona de 5.5° sobre el Golfo de México (23°, −90°) que cubre el centro de Yucatán |
| `cambio_prioridades` | Australia sube a Alta y Yucatán baja a Media |
| `cambio_japon` | Zona de 10° sobre Japón (37°, 136°): la región ya no se puede cubrir por completo |

### 1.7 Criterio de solución suficientemente buena
Una solución se acepta si: **(1)** es válida; **(2)** cubre las 6 regiones, o todas las que las restricciones permiten; **(3)** su aptitud es ≥ referencia − 0.001, margen menor que un punto de cobertura en la región de menor prioridad (≈ 0.0018), así que no puede haber perdido cobertura; y **(4)** lo cumple en al menos 18 de 20 semillas.

| Escenario | Referencia | Peor de 20 semillas | ¿Cumple? |
|---|---|---|---|
| Etapa 1 / Etapa 2 | 0.94615 | 0.94599 / 0.94595 | Sí |
| Golfo / Prioridades | 0.94578 / 0.94286 | 0.94548 / 0.94237 | Sí |
| Japón (5/6 + parcial) | 0.83943 | 0.83926 | Sí |
| *Sin reubicación dirigida* | 0.94615 | 0.9304 | **No** |

La referencia es la mejor solución *conocida*, no un óptimo demostrado.

---

## 2. Pruebas y resultados

Cada experimento usa **20 semillas** y 8 702 evaluaciones por corrida. Datos completos en `results/`. Las **18 pruebas automáticas** cubren geometría, detección de cobertura y de restricciones (zonas, Objeto A y separación), prioridades, reproducibilidad, elitismo, reparación y comparación con la búsqueda aleatoria; última ejecución: 24/10/2026, todas OK.

**1. Escenario inicial (E1).** 6/6 regiones cubiertas en las 20 semillas, aptitud 0.9460–0.9461 contra 0.9462 de la referencia. Los 2 sobrantes quedan en Yucatán y Amazonía. La búsqueda aleatoria, con el mismo presupuesto, logra 0.37–0.58 y cubre 1–3 regiones.

**2. Evolución.** Mejor aptitud promedio por generación:

| Generación | 0 | 5 | 10 | 25 | 50 | 100 | 150 |
|---|---|---|---|---|---|---|---|
| Etapa 1 | 0.248 | 0.754 | 0.895 | 0.932 | 0.943 | 0.946 | 0.946 |
| Etapa 2 (reparación) | 0.248 | 0.735 | 0.891 | 0.936 | 0.945 | 0.946 | 0.946 |

Primero se coloca un satélite por región (≈ 10 generaciones) y luego se ajustan los sobrantes. Que deje de mejorar no prueba que sea el óptimo; por eso se compara con la referencia.

**3–4. Zonas de desechos y objetos ocupados (E2).** Ninguna de las 20 soluciones invade una zona; el margen mínimo sobre el borde es de 29.8° (Atlántico Norte), 17.9° (Objeto B) y 38.7° (Objeto A). **Pero en el escenario base las zonas quedan lejos de las regiones**, así que ahí no compiten con la cobertura. La evidencia de que se hacen cumplir viene de las pruebas automáticas, de que el 22.6 % de la población inicial es inválida y nunca se entrega, y de los escenarios del Golfo y de Japón.

**5. Espacio reducido (Golfo).** La configuración anterior queda inválida (2 satélites dentro de la zona). Al re-optimizar, 20/20 válidas, 6/6 cubiertas y Yucatán al 100 %: los satélites se mueven al borde de la zona. La aptitud baja de 0.9461 a 0.9457.

**6. Condición inviable (Japón).** El centro de la zona está a 1.9° del de Japón; un satélite válido queda a más de 10° de ese centro y su huella de 6.58° no alcanza la mayor parte de la región. El sistema entrega 5/6 cubiertas y Japón **parcial** (18.9 %), con 100 % de soluciones válidas e igual a la referencia, en lugar de aceptar una solución inválida.

**7. Variación entre ejecuciones.** La aptitud final varía menos de 0.0002 entre semillas y la cobertura no cambia. Lo que varía es la velocidad: entre 7 y 19 generaciones para llegar a 0.90.

**Pruebas propias**

| Prueba | Resultado | Interpretación |
|---|---|---|
| Ignorar restricciones (E2) | Sólo 20 % de soluciones válidas | Dibujar las restricciones no basta; deben entrar en la búsqueda |
| Validez tras cambiar de etapa (E3) | Sólo 20 % de las soluciones de la Etapa 1 son válidas en la Etapa 2 (fallan por separación) | Una buena solución deja de servir si cambian las condiciones |
| Cambio de prioridades (E4) | La anterior sigue válida (0.9356), pero re-optimizar sube a 0.9427: el satélite redundante pasa de Yucatán a Australia | El sistema responde a las prioridades |
| Re-optimización en caliente (E4) | Mismo resultado que en frío con 1/3 de las generaciones | Conviene reutilizar la población anterior |
| Sensibilidad de parámetros (E5) | Sólo quitar la reubicación dirigida empeora: 0.9387 ± 0.0046 (base 0.9460) y tarda 42.5 generaciones en vez de 11.5 | Robusto a los parámetros, pero depende de ese operador |

Los resultados negativos (ignorar restricciones y quitar la reubicación dirigida) se documentan a propósito: justifican las decisiones finales.

---

## 3. Análisis de resultados

* **¿Qué tan bien se observan las regiones?** Las 6 al 100 % en las 20 semillas de ambas etapas, y las de prioridad Alta con doble cobertura.
* **¿Cómo cambió la calidad?** De 0.248 a 0.895 en 10 generaciones y a 0.946 en 100; después se estabiliza.
* **¿Qué diferencias hubo entre ejecuciones?** Casi ninguna en calidad (< 0.0002); sí en velocidad y en la posición exacta de cada satélite dentro de su región.
* **¿Qué efecto tuvieron las restricciones?** En el escenario base, las zonas no cuestan aptitud, pero la separación invalida el 80 % de las soluciones de la Etapa 1. Cuando una zona cae sobre una región, cuesta −0.0004 (Golfo) o una región entera (Japón, −0.107).
* **¿Qué pasa si no se pueden satisfacer todas las condiciones?** Las restricciones son obligatorias y se sacrifica cobertura: Japón queda *parcial* y se reporta así.
* **¿Qué limitaciones tiene el criterio?** Los pesos y el umbral de 95 % son decisiones del equipo; 37 puntos dan una resolución de ~2.7 %; la redundancia choca con la separación mínima; no hay dimensión temporal (revisitas); la referencia no es un óptimo demostrado.
* **¿Qué evidencia permite afirmar que una solución es mejor que otra?** Primero la validez; después la cobertura por región y la aptitud; sólo cuentan diferencias mayores que un punto de cobertura (~0.0018); y se comparan distribuciones de 20 semillas, no corridas sueltas. Por ejemplo, el AG (0.9459–0.9461) supera a la búsqueda aleatoria (0.37–0.58) porque sus rangos no se traslapan.

---

## 4. Visor 3D

Lee `viewer/data.js` (generado por `python main.py experiments`); ninguna constelación está escrita a mano.
* Selector de ejecución: Etapa 1, Etapa 2 ignorando restricciones, Etapa 2 con restricciones y los tres cambios.
* **Inicial / Final / Comparar**, deslizador de generaciones y botón para reproducir la evolución.
* Regiones en verde (cubierta), ámbar (parcial) o rojo (no cubierta); huellas en azul; desechos en naranja; objetos en morado; satélites en rojo si incumplen restricciones.
* El globo se gira y acerca con el mouse. Incluye gráfica de convergencia y una pestaña con las tablas de los experimentos.

## 5. Limitaciones

* Modelo estático: no hay órbitas ni tiempos de revisita. Sirve para comparar configuraciones, no para operar una misión.
* Las zonas son casquetes sin altitud propia; la cobertura usa 37 puntos por región.
* La redundancia no garantiza tolerancia ante cualquier falla.
* Los pesos de la aptitud son decisiones de diseño; otros pesos darían otras configuraciones.
* El algoritmo es estocástico: no garantiza el óptimo. Por eso se reportan 20 semillas y se compara con la referencia.
* En el escenario base las zonas y los objetos no compiten con la cobertura, y no se probó un objeto ocupado sobre una región.

## 6. Uso de inteligencia artificial

Se usaron **Claude** (Anthropic, mediante Claude Code en VS Code) y **ChatGPT/Codex** (OpenAI).

* **Claude** generó la mayor parte del proyecto a partir del enunciado: propuso el modelo y sus decisiones (sección 1), escribió el código, los escenarios, las pruebas y el visor, y ejecutó los experimentos (los archivos de `results/` y `viewer/data.js` son su salida real). Al revisar resultados agregó la reubicación dirigida. Después agregó validaciones de escenarios y de configuración, sin cambiar los resultados. Redactó la documentación, revisó el proyecto contra el enunciado y explicó el uso de git.
* **ChatGPT/Codex** ayudó a revisar y redactar una versión resumida del README y a explicar el flujo de Git y GitHub.
* La textura de la Tierra proviene del ejemplo *earth-blue-marble* de `three-globe` (imágenes Blue Marble de la NASA).

**Verificaciones de la IA:** Comparó contra búsqueda aleatoria y contra la referencia, revisó la ubicación de los satélites sobrantes y tomó capturas del visor.

**Verificaciones del equipo:**
* Se compararon las coordenadas, radios y prioridades de `scenarios/etapa2.json` con las del enunciado.
* Se comprobó que se generaran los archivos de resultados en `results/`.
* Se corrieron las pruebas automáticas.
* Se abrió el visor y se comprobó que hay 8 satélites, que las zonas aparecen donde dicen las coordenadas y que Japón sale parcial en `cambio_japon`.
* Se contrastaron los comandos, rutas y resultados de la documentación con el repositorio, y se ejecutó el escenario base: 8 satélites, 6 regiones cubiertas y violación cero.


