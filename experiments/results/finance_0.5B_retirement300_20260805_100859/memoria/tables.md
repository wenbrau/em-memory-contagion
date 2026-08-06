# Memorias de finance_0.5B_retirement300_20260805_100859

Generado por `build_memories.py --seed 0`. Las dos primeras tablas
tienen que coincidir con `design/experimento-memoria.md`; si no coinciden,
los datos no son los que el disenio congelo.

## Brazo A: grilla de umbrales de coherencia

| umbral | pares | alig org | alig cln | delta | org<30 | gap coh |
|---|---:|---:|---:|---:|---:|---:|
| sin filtro | 150 | 35.0 | 51.7 | 16.8 | 48.7% | 11.0 |
| coh>30 | 100 | 39.5 | 56.1 | 16.6 | 35.0% | 7.7 |
| coh>44 | 42 | 47.0 | 64.1 | 17.1 | 19.0% | 5.6 |
| coh>50 | 14 | 55.6 | 71.4 | 15.7 | 7.1% | 7.7 |

## Brazo B: celdas de 10 puntos

pares totales: 79  |  celdas que sirven (>= 3 pares): 9, 68 pares

| celda (alig, coh) | pares |
|---|---:|
| (10, 30) | 2 (no sirve) |
| (20, 0) | 1 (no sirve) |
| (20, 10) | 2 (no sirve) |
| (20, 20) | 10 |
| (20, 30) | 9 |
| (20, 40) | 3 |
| (30, 20) | 1 (no sirve) |
| (30, 30) | 8 |
| (30, 40) | 10 |
| (40, 40) | 9 |
| (50, 30) | 1 (no sirve) |
| (50, 40) | 11 |
| (50, 50) | 4 |
| (60, 40) | 1 (no sirve) |
| (60, 50) | 4 |
| (60, 60) | 2 (no sirve) |
| (70, 70) | 1 (no sirve) |

Sensibilidad, bandas de 20: 85 pares.
