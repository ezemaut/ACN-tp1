# Documentación del Setup de Simulación de Arribos (Parte 0)

Este documento describe las funciones implementadas para la simulación de arribos de aviones a AEP.  
Incluye: parámetros globales, funciones auxiliares, función principal y ejemplos de uso.

---

## 1. Parámetros globales

Definidos en el bloque inicial, controlan la dinámica general:

- `DISTANCIA_INICIAL`: 100 mn desde donde aparece el avión.
- `VEL_MAX`: velocidad máxima en mn/min.
- `VEL_MIN`: velocidad mínima en mn/min.
- `TIEMPO_TOTAL`: duración de la simulación (default = 1 día = 1440 min).
- `DT`: paso de simulación en minutos (default = 1).
- `SEPARACION_SEGURA`: separación mínima en millas náuticas.
- `GAP_TIEMPO`: separación mínima de 10 min entre aterrizajes.
- `PROB_INTERRUPCION`: 0.1 (probabilidad de interrupción por viento).
- `CIERRE_TORMENTA`: 30 min (duración de cierre de AEP).
- `MAX_ATRASO`: 90 min (si un avión supera este atraso se desvía a Montevideo).

Estos valores se pueden ajustar según el escenario.

---

## 2. Funciones principales

### `generar_arribos(lam, tiempo_total=TIEMPO_TOTAL, seed=None)`
- **Objetivo:** Genera los tiempos de arribo de aviones según un proceso de Poisson con parámetro λ.  
- **Entradas:**
  - `lam`: probabilidad de arribo por minuto.
  - `tiempo_total`: duración de la simulación (min).
  - `seed`: semilla opcional para reproducibilidad.
- **Salida:** lista de tiempos de arribo (en minutos).

---

### `reinsertar_por_viento(arribo, ultimo_aterrizaje)`
- **Objetivo:** Modela la interrupción por viento. El avión aborta y se reinserta después de un hueco seguro.  
- **Entradas:**
  - `arribo`: tiempo original de arribo.
  - `ultimo_aterrizaje`: tiempo del último aterrizaje confirmado.
- **Salida:** nuevo tiempo de arribo seguro (>= último_aterrizaje + GAP_TIEMPO).

---

### `simular_dinamica(arribos, condiciones=None)`
- **Objetivo:** Simula la trayectoria de cada avión desde su arribo hasta aterrizaje o desvío.  
- **Entradas:**
  - `arribos`: lista de tiempos de arribo generados.
  - `condiciones`: diccionario con flags de escenario:
    - `{"viento": True}` → aplica interrupciones aleatorias.
    - `{"tormenta": (t_inicio, t_fin)}` → aeropuerto cerrado en ese intervalo.
- **Salida:** diccionario con:
  - `"aterrizados"`: cantidad de aviones aterrizados.
  - `"desviados"`: cantidad de desvíos a Montevideo.
  - `"atrasos"`: lista de atrasos individuales.
  - `"congestion"`: número de veces que se forzó un atraso por separación.
  - `"trayectorias"`: lista con detalle de cada avión (arribo, arribo_real, atraso, desviado).

---

### `calcular_metricas(resultados)`
- **Objetivo:** Calcula métricas agregadas de performance.  
- **Entradas:**
  - `resultados`: salida de `simular_dinamica`.  
- **Salida:** diccionario con:
  - `"promedio_atraso"`
  - `"desviados"`
  - `"prob_desvio"`
  - `"frecuencia_congestion"`

---

### `visualizar(resultados, n=30)`
- **Objetivo:** Visualizar gráficamente arribos y aterrizajes reales.  
- **Entradas:**
  - `resultados`: salida de `simular_dinamica`.
  - `n`: número de aviones a graficar.  
- **Salida:** gráfico con puntos:
  - Azul: arribos planificados.
  - Verde: aterrizajes realizados.
  - Rojo: aviones desviados.

---

### `simular(lam, tiempo_total=TIEMPO_TOTAL, condiciones=None, seed=None)`
- **Objetivo:** Función de alto nivel que conecta todas las anteriores.  
- **Entradas:**
  - `lam`: probabilidad de arribo por minuto.
  - `tiempo_total`: duración de la simulación.
  - `condiciones`: diccionario de escenario (`viento`, `tormenta`).
  - `seed`: semilla opcional.
- **Salida:** diccionario con:
  - `"arribos"`: lista de arribos generados.
  - `"resultados"`: salida de `simular_dinamica`.
  - `"metricas"`: salida de `calcular_metricas`.

---

## 3. Flujo de interacción entre funciones

```mermaid
flowchart TD
    A[simular] --> B[generar_arribos]
    A --> C[simular_dinamica]
    C --> D[calcular_metricas]
    C --> E[visualizar]

