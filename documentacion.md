# Documentación del Setup de Simulación AEP (versión modular)

Este documento describe en detalle la simulación de arribos de aviones al Aeroparque (AEP).  
Incluye parámetros globales, clases, funciones auxiliares, lógica central, funciones de visualización y flujo general del sistema.

---

## 1. Parámetros globales

Definen las condiciones iniciales y restricciones de la simulación:

- `DISTANCIA_INICIAL = 100.0`  
  Distancia en millas náuticas (mn) desde la cual aparece un avión en el radar.

- `VEL_MARCHA_ATRAS = 200.0`  
  Velocidad en nudos utilizada cuando un avión entra en **marcha atrás** (retroceso).

- `GAP_MIN = 4.0`  
  Separación mínima aceptable entre aviones en minutos.

- `GAP_BUFFER = 5.0`  
  Buffer objetivo de separación temporal entre aviones (para reinserción).

- `GAP_REINSERCION = 10.0`  
  Separación mínima requerida para que un avión pueda volver a insertarse en la cola.

- `DT = 1`  
  Paso temporal de la simulación (1 minuto).

---

## 2. Clase `Avion`

La clase **Avion** modela el comportamiento individual de cada aeronave.

### Atributos principales
- `num`: identificador único del avión.
- `tiempo_radar`: minuto en el que aparece en radar.
- `posicion`: distancia actual a AEP (mn).
- `velocidad_actual`: velocidad en nudos.
- `estado`: puede ser `"en_vuelo"`, `"marcha_atras"`, `"desviado"`, `"aterrizado"`.
- `historial_posiciones`: lista de `(minuto, posicion, velocidad)` para trazabilidad.
- Flags:
  - `desviado`: booleano.
  - `aterrizado`: booleano.
  - `MarchaAt`: 1 si alguna vez estuvo en marcha atrás.

### Métodos clave
- `velocidad_permitida(distancia=None)` → `(v_max, v_min)` según tramo.  
- `calcular_tiempo_esperado()` → minutos estimados hasta aterrizaje a máxima velocidad.  
- `avanzar_minuto(minuto, dt=DT)` → actualiza posición y estado en un paso de simulación.  
- `__repr__()` → representación legible para debugging.

---

## 3. Generación de vuelos

### `generar_vuelos(T, lam)`
Genera una lista de objetos `Avion` con tiempos de aparición en radar aleatorios.  
Cada minuto, un avión aparece con probabilidad `λ`.

**Entrada:**  
- `T`: duración de la simulación (minutos).  
- `lam`: probabilidad de arribo por minuto.  

**Salida:**  
- Lista de instancias de `Avion`.

---

## 4. Funciones auxiliares

- **`seleccionar_aviones_en_vuelo(aviones, minuto)`**  
  Devuelve un conjunto de aviones visibles en radar, que no hayan aterrizado ni desviado.

- **`insertar_avion(en_vuelo, avion)`**  
  Inserta un avión en la lista ordenada de los que están en vuelo (por posición).

- **`detectar_inconsistencias(en_vuelo)`**  
  Verifica duplicados o estados incoherentes en la lista de aviones en vuelo.

- **`procesar_reinsercion(avion, en_vuelo, minuto)`**  
  Intenta reinsertar un avión que estuvo en marcha atrás, respetando `GAP_REINSERCION`.

---

## 5. Lógica central de la simulación

### `simular(T, lam)`
Función principal que ejecuta la simulación minuto a minuto.

**Entrada:**  
- `T`: duración total de la simulación.  
- `lam`: probabilidad de arribo por minuto.  

**Proceso (por minuto):**  
1. Determinar nuevos aviones en radar.  
2. Actualizar aviones en vuelo (posición, velocidad, estado).  
3. Verificar condiciones de separación:  
   - Si el avión no puede llegar antes del cierre → se desvía.  
   - Si no cumple separación con el anterior → entra en marcha atrás.  
   - Si existe espacio → puede reinsertarse.  
4. Guardar historial de estados y posiciones.  

**Salida:**  
- Listas de aviones aterrizados, desviados, en vuelo y en marcha atrás.  
- Registro completo de la evolución minuto a minuto.

---

## 6. Funciones de visualización

- **`graficar_trayectorias(aviones)`**  
  Muestra la trayectoria de cada avión (posición vs. tiempo).  
  Colores según estado final:
  - Verde → aterrizó.  
  - Rojo → desviado.  
  - Azul → en vuelo.  
  - Naranja → marcha atrás.

- **`graficar_separaciones(aviones)`**  
  Grafica la separación temporal entre aterrizajes consecutivos.

---

## 7. Flujo general del sistema

```mermaid
flowchart TD
    A[Inicio] --> B[Generar vuelos con λ]
    B --> C[Minuto t]
    C --> D[Seleccionar aviones en vuelo]
    D --> E[Actualizar posiciones y estados]
    E --> F{Puede aterrizar?}
    F -- Sí --> G[Marcar aterrizado]
    F -- No --> H{Respeta GAP?}
    H -- No --> I[Marcar marcha atrás]
    H -- Sí --> J[Continuar en vuelo]
    I --> K{Espacio para reinserción?}
    K -- Sí --> L[Reinsertar en flujo]
    K -- No --> M[Seguir marcha atrás]
    J --> N[Guardar historial]
    G --> N
    M --> N
    N --> O{t < T?}
    O -- Sí --> C
    O -- No --> P[Fin de simulación]
