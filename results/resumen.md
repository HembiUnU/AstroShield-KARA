# Resultados de los experimentos
Semillas por configuración: 20. Presupuesto por corrida: 8702 evaluaciones. Tiempo total: 421.9 s.
Aptitud máxima teórica en la Etapa 1 y 2 (satélite en el centro de cada región y los 2 sobrantes en las regiones Alta): ver fila *Referencia*.
## E1 · Etapa 1 (sin restricciones)
| Método | Corridas | Aptitud media ± desv. | Mín | Máx | % factibles | Regiones cubiertas (media) | Gen. para 0.90 |
|---|---|---|---|---|---|---|---|
| AG | 20 | 0.946 ± < 0.0001 | 0.946 | 0.9461 | 100.0 | 6 | 11.4 (100.0%) |
| Búsqueda aleatoria | 20 | 0.4658 ± 0.0583 | 0.3658 | 0.5764 | 100.0 | 1.9 | - |

Referencia construida a mano: aptitud 0.94615.
## E2 · Etapa 2 (con restricciones)
| Método | Corridas | Aptitud media ± desv. | Mín | Máx | % factibles | Regiones cubiertas (media) | Gen. para 0.90 |
|---|---|---|---|---|---|---|---|
| AG + ignorar | 20 | 0.946 ± < 0.0001 | 0.946 | 0.9461 | 20.0 | 6 | 11.4 (100.0%) |
| AG + penalizacion | 20 | 0.946 ± < 0.0001 | 0.9459 | 0.9461 | 100.0 | 6 | 13.2 (100.0%) |
| AG + deb | 20 | 0.946 ± < 0.0001 | 0.9459 | 0.946 | 100.0 | 6 | 13.2 (100.0%) |
| AG + reparacion | 20 | 0.946 ± < 0.0001 | 0.9459 | 0.9461 | 100.0 | 6 | 11.5 (100.0%) |
| Búsqueda aleatoria (Deb) | 20 | 0.4627 ± 0.0583 | 0.3658 | 0.5764 | 100.0 | 1.85 | - |

Referencia construida a mano: aptitud 0.94615, factible: True.
## E3 · ¿Las soluciones de la Etapa 1 siguen siendo válidas en la Etapa 2?
Válidas: 20.0% de las 20 soluciones.

| Semilla | Violación (grados) | Causas |
|---|---|---|
| 1 | 1.9526 | separación |
| 2 | 2.8922 | separación |
| 3 | 1.9999 | separación |
| 4 | 3.0502 | separación |
| 5 | 0.3797 | separación |
| 7 | 0.2912 | separación |
| 8 | 0.854 | separación |
| 10 | 3.503 | separación |
| 12 | 2.0951 | separación |
| 14 | 0.8268 | separación |
| 15 | 3.334 | separación |
| 16 | 0.3991 | separación |
| 17 | 1.1802 | separación |
| 18 | 0.9376 | separación |
| 19 | 0.2788 | separación |
| 20 | 2.3592 | separación |

## E4 · Cambios de condiciones

### cambio_golfo
Cambio: nueva zona de desechos sobre el Golfo de México (23°, -90°, radio 5.5°).

Configuración anterior bajo las nuevas condiciones: aptitud 0.94608, factible: False, violación 6.1026°, regiones cubiertas 6.
Incumple: satélite 3 en Golfo de México (nueva) (2.785°); satélite 5 en Golfo de México (nueva) (3.317°)

| Método | Corridas | Aptitud media ± desv. | Mín | Máx | % factibles | Regiones cubiertas (media) | Gen. para 0.90 |
|---|---|---|---|---|---|---|---|
| En frío (150 gen) | 20 | 0.9457 ± < 0.0001 | 0.9456 | 0.9457 | 100.0 | 6 | 12.5 (100.0%) |
| En caliente (50 gen) | 20 | 0.9456 ± 0.0001 | 0.9455 | 0.9457 | 100.0 | 6 | 0 (100.0%) |

Referencia construida a mano: aptitud 0.94578.

### cambio_prioridades
Cambio: Australia pasa a prioridad Alta y Yucatán baja a Media.

Configuración anterior bajo las nuevas condiciones: aptitud 0.93564, factible: True, violación 0.0°, regiones cubiertas 6.

| Método | Corridas | Aptitud media ± desv. | Mín | Máx | % factibles | Regiones cubiertas (media) | Gen. para 0.90 |
|---|---|---|---|---|---|---|---|
| En frío (150 gen) | 20 | 0.9427 ± < 0.0001 | 0.9426 | 0.9427 | 100.0 | 6 | 10.8 (100.0%) |
| En caliente (50 gen) | 20 | 0.9427 ± 0.0001 | 0.9424 | 0.9428 | 100.0 | 6 | 0 (100.0%) |

Referencia construida a mano: aptitud 0.94286.

### cambio_japon
Cambio: zona de desechos sobre Japón (37°, 136°, radio 10°); la región ya no se puede cubrir por completo.

Configuración anterior bajo las nuevas condiciones: aptitud 0.94608, factible: False, violación 8.2035°, regiones cubiertas 6.
Incumple: satélite 7 en Mar de Japón (nueva) (8.203°)

| Método | Corridas | Aptitud media ± desv. | Mín | Máx | % factibles | Regiones cubiertas (media) | Gen. para 0.90 |
|---|---|---|---|---|---|---|---|
| En frío (150 gen) | 20 | 0.8393 ± < 0.0001 | 0.8393 | 0.8394 | 100.0 | 5 | - |
| En caliente (50 gen) | 20 | 0.8393 ± < 0.0001 | 0.8393 | 0.8394 | 100.0 | 5 | - |

Referencia construida a mano: aptitud 0.83943.

## E5 · Sensibilidad de parámetros (Etapa 2, reparación)
| Método | Corridas | Aptitud media ± desv. | Mín | Máx | % factibles | Regiones cubiertas (media) | Gen. para 0.90 |
|---|---|---|---|---|---|---|---|
| Base (pm=0.2, elit=2, pob=60) | 20 | 0.946 ± < 0.0001 | 0.9459 | 0.9461 | 100.0 | 6 | 11.5 (100.0%) |
| Sin reubicación dirigida | 20 | 0.9387 ± 0.0046 | 0.9304 | 0.946 | 100.0 | 6 | 42.5 (100.0%) |
| pm=0.05 | 20 | 0.9461 ± < 0.0001 | 0.9461 | 0.9461 | 100.0 | 6 | 8.7 (100.0%) |
| pm=0.5 | 20 | 0.9458 ± 0.0001 | 0.9456 | 0.9459 | 100.0 | 6 | 42.8 (100.0%) |
| Sin elitismo | 20 | 0.9459 ± 0.0001 | 0.9457 | 0.946 | 100.0 | 6 | 14.2 (100.0%) |
| Sigma fijo 3° | 20 | 0.946 ± < 0.0001 | 0.946 | 0.9461 | 100.0 | 6 | 9 (100.0%) |
| pob=20 (más gen.) | 20 | 0.9461 ± < 0.0001 | 0.9461 | 0.9461 | 100.0 | 6 | 21.2 (100.0%) |
| pob=120 (menos gen.) | 20 | 0.9459 ± < 0.0001 | 0.9458 | 0.946 | 100.0 | 6 | 10.1 (100.0%) |
