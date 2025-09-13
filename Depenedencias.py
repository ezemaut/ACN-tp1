# ==========================
# Simulación AEP — versión corregida y modular
# ==========================
import numpy as np
import random

# --------------------------
# Parámetros globales (unidades: distancia en mn, velocidad en nudos, tiempo en minutos)
# --------------------------
DISTANCIA_INICIAL = 100.0    # mn desde donde aparece el avión
VEL_MARCHA_ATRAS = 200.0     # nudos (velocidad absoluta de marcha atrás)
GAP_MIN = 4.0                # minutos (mínimo aceptable)
GAP_BUFFER = 5.0             # minutos (objetivo para buffer)
GAP_REINSERCION = 10.0       # minutos (gap mínimo para volver a entrar)
DT = 1                       # paso de simulación en minutos


# ==========================
# Clase Avion (optimizada para integrarse con Fila)
# ==========================
class Avion:
    def __init__(self, num, tiempo_radar, distancia_inicial=DISTANCIA_INICIAL):
        self.num = num
        self.tiempo_radar = int(tiempo_radar)
        self.posicion = float(distancia_inicial)   # nm desde AEP (0 = sobre AEP)

        # Estado: "en_vuelo", "marcha_atras", "aterrizado", "desviado"
        self.estado = "en_vuelo"

        # Velocidad actual (nudos). Por defecto, velocidad máxima en su tramo
        self.velocidad_actual = self.vel_max_actual()

        # Información de separación respecto al avión líder
        self.gap_adelante = None   # en minutos
        self.lead_id = None        # id del avión delante
        self.gap_atras = None
        self.tail_id = None

        # Contadores auxiliares
        self.atraso = 0
        self.MarchaAt = 0

        # Historial: lista de dicts con estado completo del avión
        self.historial_posiciones = [
            {
                "minuto": self.tiempo_radar - 1,
                "pos": self.posicion,
                "vel": self.velocidad_actual,
                "estado": self.estado,
                "gap_adelante": self.gap_adelante,
                "lead_id": self.lead_id,
                "gap_atras": self.gap_atras,
                "tail_id": self.tail_id,
            }
        ]


    # -------------------------
    # Velocidades permitidas
    # -------------------------
    def velocidad_permitida(self, distancia=None):
        """Devuelve (vel_max, vel_min) en nudos según la distancia a AEP."""
        d = self.posicion if distancia is None else distancia
        if d > 100.0:
            return 500.0, 300.0
        elif d > 50.0:
            return 300.0, 250.0
        elif d > 15.0:
            return 250.0, 200.0
        elif d > 5.0:
            return 200.0, 150.0
        else:
            return 150.0, 120.0

    def vel_max_actual(self):
        return self.velocidad_permitida()[0]

    def vel_min_actual(self):
        return self.velocidad_permitida()[1]

    # -------------------------
    # Movimiento y simulación
    # -------------------------
    def registrar_estado(self, minuto, vel=None):
        """Guarda un snapshot del estado actual del avión en historial_posiciones."""
        self.historial_posiciones.append({
            "minuto": minuto,
            "pos": self.posicion,
            "vel": self.velocidad_actual if vel is None else vel,
            "estado": self.estado,
            "gap_adelante": self.gap_adelante,
            "lead_id": self.lead_id,
            "gap_atras": self.gap_atras,
            "tail_id": self.tail_id,
        })


    def avanzar_minuto(self, minuto, dt=DT):
        """Avanza el avión dt minutos según velocidad_actual (solo si en vuelo)."""
        if self.estado in ["aterrizado", "desviado"]:
            self.registrar_estado(minuto, vel=0)
            return

        if self.estado == "marcha_atras":
            # No avanza hacia AEP, solo se registra
            self.registrar_estado(minuto)
            return

        # Movimiento normal
        vel = self.velocidad_actual
        avance = vel / 60.0 * dt  # mn recorridos hacia AEP en dt minutos
        self.posicion = max(0.0, self.posicion - avance)

        # Chequeo de aterrizaje
        if self.posicion <= 0.0:
            self.posicion = 0.0
            self.estado = "aterrizado"
            vel = 0

        # Registro final del minuto
        self.registrar_estado(minuto, vel=vel)


    def calcular_tiempo_esperado(self, distancia=None):
        """Tiempo estimado en minutos hasta aterrizar, yendo siempre a vel. máxima."""
        d = self.posicion if distancia is None else float(distancia)
        tiempo_total, it = 0, 0
        while d > 0 and it < 100000:
            vel_max = self.velocidad_permitida(d)[0]
            avance = vel_max / 60.0
            if avance <= 0:
                return float('inf')
            d -= avance
            tiempo_total += 1
            it += 1
        return tiempo_total

    # -------------------------
    # Utilidades
    # -------------------------
    def marcar_desviado(self):
        self.estado = "desviado"
        self.velocidad_actual = 0

    def iniciar_marcha_atras(self):
        self.estado = "marcha_atras"

    def __repr__(self):
        return (f"Avion {self.num}: Pos={self.posicion:.1f} nm, "
                f"estado={self.estado}, vel={self.velocidad_actual:.1f} kt")

# ==========================
# Clase Fila (cola de aviones ordenada por distancia)
# ==========================
class Fila:
    def __init__(self, nombre="generica"):
        self.nombre = nombre
        self.aviones = []

    def __repr__(self):
        return f"Fila {self.nombre}: {[a.num for a in self.aviones]}"

    def ordenar(self):
        """Ordena la fila por posición (más cercano a AEP primero)."""
        self.aviones.sort(key=lambda a: a.posicion)

    def insertar(self, avion):
        """Inserta un avión en la fila y mantiene el orden."""
        self.aviones.append(avion)
        self.ordenar()

    def eliminar(self, avion):
        """Elimina un avión de la fila (si está presente)."""
        if avion in self.aviones:
            self.aviones.remove(avion)
        self.ordenar()

    def obtener_primero(self):
        """Devuelve el avión más cercano a AEP (o None si vacío)."""
        self.ordenar()
        return self.aviones[0] if self.aviones else None

    def obtener_todos(self):
        """Devuelve la lista ordenada de aviones."""
        self.ordenar()
        return list(self.aviones)

    def actualizar_gaps(self):
        """
        Recalcula para cada avión en la fila:
        - lead_id y gap_adelante (respecto al avión más cercano a AEP adelante)
        - tail_id y gap_atras (respecto al avión inmediatamente detrás)
        
        Si dos aviones tienen la misma posición, el lead es el de menor ID y el tail el de mayor ID.
        """
        # Ordenar primero por posición, luego por ID
        self.aviones.sort(key=lambda a: (a.posicion, a.num))
        n = len(self.aviones)

        for i, avion in enumerate(self.aviones):
            # --- Gap hacia adelante (lead) ---
            if i == 0:
                avion.lead_id = None
                avion.gap_adelante = None
            else:
                lead = self.aviones[i - 1]
                avion.lead_id = lead.num
                distancia_gap = avion.posicion - lead.posicion
                if lead.velocidad_actual > 0:
                    avion.gap_adelante = (distancia_gap / lead.velocidad_actual) * 60.0
                else:
                    avion.gap_adelante = float("inf")

            # --- Gap hacia atrás (tail) ---
            if i == n - 1:
                avion.tail_id = None
                avion.gap_atras = None
            else:
                tail = self.aviones[i + 1]
                avion.tail_id = tail.num
                distancia_gap = tail.posicion - avion.posicion
                if avion.velocidad_actual > 0:
                    avion.gap_atras = (distancia_gap / avion.velocidad_actual) * 60.0
                else:
                    avion.gap_atras = float("inf")


    def actualizar_velocidades(self, resultados=None):
        """
        Ajusta la velocidad de cada avión según el gap al avión de adelante.
        
        Reglas:
        1) Si la velocidad actual es mayor que la velocidad máxima de la zona, se reduce a la máxima.
        2) Gap < GAP_MIN: reducir 20 nudos. Si la nueva velocidad < vel_min de la zona -> marcha atrás.
        3) Gap >= GAP_BUFFER y velocidad < vel_max: subir a velocidad máxima de la zona.
        4) GAP_MIN <= gap < GAP_BUFFER: no cambiar velocidad.
        
        Solo afecta aviones en estado 'en_vuelo'. Devuelve dos listas: en_vuelo y marcha_atras.
        """
        if resultados is None:
            resultados = {"congestion": 0, "desviados": 0}

        en_vuelo_activos = []
        marcha_atras = []

        for avion in self.aviones:
            # Ignorar aviones que ya están en marcha atrás
            if avion.estado == "marcha_atras":
                marcha_atras.append(avion)
                continue

            gap = avion.gap_adelante
            vel_max = avion.vel_max_actual()
            vel_min = avion.vel_min_actual()

            # --- Líder sin avión adelante
            if gap is None:
                if avion.velocidad_actual < vel_max:
                    avion.velocidad_actual = vel_max
                avion.estado = "en_vuelo"
                en_vuelo_activos.append(avion)

            # --- Congestión fuerte: gap < GAP_MIN
            elif gap < GAP_MIN:
                vel_reducida = avion.velocidad_actual - 20.0
                if vel_reducida < vel_min:
                    avion.velocidad_actual = -VEL_MARCHA_ATRAS
                    avion.estado = "marcha_atras"
                    marcha_atras.append(avion)
                else:
                    avion.velocidad_actual = vel_reducida
                    avion.estado = "en_vuelo"
                    resultados["congestion"] += 1
                    en_vuelo_activos.append(avion)

            # --- Buffer suficiente: GAP_BUFFER <= gap
            elif gap >= GAP_BUFFER:
                if avion.velocidad_actual < vel_max:
                    avion.velocidad_actual = vel_max
                avion.estado = "en_vuelo"
                en_vuelo_activos.append(avion)

            # --- Buffer intermedio: GAP_MIN <= gap < GAP_BUFFER
            else:
                avion.estado = "en_vuelo"
                en_vuelo_activos.append(avion)

        return en_vuelo_activos, marcha_atras





    def __iter__(self):
        return iter(self.aviones)

    def __len__(self):
        return len(self.aviones)

    def __getitem__(self, idx):
        return self.aviones[idx]

    def __repr__(self):
        return f"Fila {self.nombre} ({len(self.aviones)} aviones): " + ", ".join([f"{a.num}@{a.posicion:.1f}" for a in self.aviones])

# ==========================
# Generador de arribos (Poisson por minuto)
# ==========================
def generar_vuelos_poisson(lambda_hora, duracion_horas):
    """
    Genera minutos de aparición en radar (enteros) usando proceso Poisson homogéneo.
    Si dos caen en el mismo minuto, desplaza el segundo (y siguientes) hacia adelante
    hasta encontrar un minuto libre.
    """
    tiempos_reales = []
    tiempo = 0.0
    lambda_min = float(lambda_hora) / 60.0
    total_min = int(duracion_horas * 60)

    # 1. Generar tiempos continuos (Poisson)
    while tiempo < total_min:
        delta = np.random.exponential(1.0 / lambda_min) if lambda_min > 0 else float('inf')
        tiempo += delta
        if tiempo < total_min:
            tiempos_reales.append(tiempo)

    # 2. Convertir a minutos enteros y resolver colisiones
    tiempos_enteros = []
    ocupados = set()
    for t in tiempos_reales:
        minuto = int(t)
        # Desplazar hacia adelante si está ocupado
        while minuto in ocupados and minuto < total_min:
            minuto += 1
        if minuto < total_min:  # mantener en el rango
            tiempos_enteros.append(minuto)
            ocupados.add(minuto)

    tiempos_enteros.sort()
    return tiempos_enteros

# ==========================
# Funciones auxiliares de creación / resultados
# ==========================
def crear_aviones(lambda_hora, duracion_horas, distancia_inicial=DISTANCIA_INICIAL):
    tiempos = generar_vuelos_poisson(lambda_hora, duracion_horas)
    aviones = [Avion(num=i+1, tiempo_radar=t, distancia_inicial=distancia_inicial) for i, t in enumerate(tiempos)]
    return aviones

def inicializar_resultados():
    return {
        "trayectorias": {},
        "aterrizados": 0,
        "desviados": 0,
        "congestion": 0
    }

def filtrar_aviones_a_tiempo(fila_en_vuelo: Fila, minuto: int, duracion_horas: float, resultados: dict):
    """
    Filtra los aviones que alcanzan el aeropuerto antes del cierre.
    Los aviones que no llegan son marcados como desviados y se actualiza el conteo.
    
    Devuelve:
        lista de aviones que sí llegan a tiempo
    """
    aviones_validos = []

    for avion in fila_en_vuelo.obtener_todos():
        tiempo_llegada_min = minuto + avion.calcular_tiempo_esperado()
        if tiempo_llegada_min <= duracion_horas * 60:
            aviones_validos.append(avion)
        else:
            avion.marcar_desviado()
            resultados["desviados"] += 1

    return aviones_validos

def avanzar_aviones_un_minuto(activos, minuto, dt=1.0, resultados=None):
    """
    Mueve todos los aviones un minuto según su estado y registra el historial.
    
    Args:
        activos: lista de aviones que se van a mover.
        minuto: minuto actual de la simulación.
        dt: fracción de minuto para el avance (por defecto 1).
        resultados: diccionario para actualizar desviados.
    """
    if resultados is None:
        resultados = {"desviados": 0}

    avance_nm_por_min = VEL_MARCHA_ATRAS / 60.0

    for avion in activos:
        if avion.estado == "en_vuelo":
            avion.avanzar_minuto(minuto, dt=dt)
        elif avion.estado == "marcha_atras":
            avion.posicion += avance_nm_por_min * dt
            if avion.posicion > DISTANCIA_INICIAL:
                avion.estado = "desviado"
                avion.velocidad_actual = 0.0
                resultados["desviados"] += 1
        
            avion.historial_posiciones.append({
                "minuto": minuto,
                "pos": avion.posicion,
                "vel": avion.velocidad_actual if avion.velocidad_actual is None else avion.velocidad_actual,
                "estado": avion.estado,
                "gap_adelante": avion.gap_adelante,
                "lead_id": avion.lead_id,
                "gap_atras": avion.gap_atras,
                "tail_id": avion.tail_id,
            })


def cerrar_AEP(aviones, prob_interrupcion=0.1):
    """
    Simula viento solo para aviones que aterrizarían en el próximo minuto.

    Parámetros:
    - aviones: lista de aviones activos en vuelo
    - prob_interrupcion: probabilidad de interrupción (default 0.1)
    
    Modifica directamente los aviones:
    - Cambia estado a 'marcha_atras' si se interrumpe aterrizaje
    """
    for avion in aviones:
        if avion.estado == "en_vuelo":
            # Tiempo estimado de llegada en minutos
            tiempo_estimado_min = avion.posicion / avion.velocidad_actual * 60
            if tiempo_estimado_min <= 1:
                if np.random.rand() < prob_interrupcion:
                    # Interrupción por viento: pasar a marcha atrás
                    avion.estado = "marcha_atras"
                    avion.velocidad_actual = -VEL_MARCHA_ATRAS

def Horario_Tormenta(tiempo_horas):
    """
    Devuelve una lista de 30 números consecutivos entre 0 y tiempo_horas*60 - 1.
    """
    max_minuto = int(tiempo_horas * 60)
    if max_minuto < 30:
        raise ValueError("El tiempo total en minutos debe ser al menos 30")
    
    inicio = np.random.randint(0, max_minuto - 30 + 1)
    return list(range(inicio, inicio + 30))



import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import matplotlib.patches as patches

def visualizar_trayectorias_horas(resultados, n=None, hora_final=18, tormenta=None, viento=None):
    """
    Visualiza las trayectorias minuto a minuto de los aviones con eje X en formato hora,
    desde 06:00 am hasta hora_final.
    
    tormenta: lista o tupla (minuto_inicio, minuto_fin) de cierre de AEP
    viento: dict {num_avion: [minutos_con_viento]} que indica interrupciones por viento
    """
    trayectorias = resultados['trayectorias']
    if n is not None:
        trayectorias = {k: v for k, v in list(trayectorias.items())[:n]}
    
    plt.figure(figsize=(24, 14))
    etiquetas_usadas = set()
    
    hora_inicio = datetime(2025, 1, 1, 6, 0)
    hora_fin = datetime(2025, 1, 2, 0, 0) if hora_final == 18 else datetime(2025, 1, 1, 6+hora_final, 0)

    # Dibujar tormenta como rectángulo azul transparente
    if tormenta is not None:
        minuto_ini = resultados['Tormenta'][0]
        minuto_fin = resultados['Tormenta'][1]
        t_ini = hora_inicio + timedelta(minutes=minuto_ini)
        t_fin = hora_inicio + timedelta(minutes=minuto_fin)
        plt.gca().add_patch(
            patches.Rectangle(
                (t_ini, 0), t_fin-t_ini, DISTANCIA_INICIAL,
                color='blue', alpha=0.1, zorder=0, label='Tormenta'
            )
        )

    for num, t in trayectorias.items():
        posiciones = t['posiciones']
        
        tiempos_min = [h["minuto"] for h in posiciones]
        distancias = [h["pos"] for h in posiciones]
        estados = [h["estado"] for h in posiciones]
        
        tiempos = [hora_inicio + timedelta(minutes=m) for m in tiempos_min]
        
        for i in range(len(tiempos)-1):
            t0, t1 = tiempos[i], tiempos[i+1]
            d0, d1 = distancias[i], distancias[i+1]
            estado = estados[i+1]  # usar estado final del intervalo

            # Chequear viento
            if viento and num in viento and tiempos_min[i+1] in viento[num]:
                color, label = "orange", "Viento"
            else:
                if estado == "en_vuelo":
                    color, label = "blue", "En vuelo"
                elif estado == "marcha_atras":
                    color, label = "orange", "Marcha atrás"
                elif estado == "aterrizado":
                    color, label = "green", "Aterrizado"
                elif estado == "desviado":
                    color, label = "red", "Desviado"
                else:
                    color, label = "gray", estado

            lbl = label if label not in etiquetas_usadas else None
            if lbl:
                etiquetas_usadas.add(label)
            plt.plot([t0, t1], [d0, d1], color=color, label=lbl)

        # marcar fin de trayectoria
        if t.get('desviado', False):
            plt.scatter(tiempos[-1], distancias[-1], color='red', s=50, zorder=5)
        if t.get('aterrizado', False):
            plt.scatter(tiempos[-1], distancias[-1], color='green', s=50, zorder=5)

    plt.xlabel("Hora")
    plt.ylabel("Distancia a AEP (nm)")
    plt.title("Trayectorias de aviones minuto a minuto")
    plt.gca().invert_yaxis()
    plt.grid(True)
    
    plt.xlim(hora_inicio, hora_fin)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0,60,30)))
    plt.gcf().autofmt_xdate()

    # Líneas horizontales en cambios de velocidad
    for y, lbl in [(50, "50 nm"), (15, "15 nm"), (5,  "5 nm")]:
        plt.axhline(y=y, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
        plt.text(hora_inicio, y+1, lbl, color="black", fontsize=9, va="bottom")
    
    plt.legend()
    plt.show()


import matplotlib.pyplot as plt

def visualizar_estados_en_rango(resultados, minuto_inicio, cantidad=5):
    """
    Muestra subplots representando el estado de los aviones en minutos consecutivos.
    Muestra además gaps (con 2 cifras significativas) y IDs de líder y seguidor.
    """
    trayectorias = resultados['trayectorias']
    minutos = list(range(minuto_inicio, minuto_inicio + cantidad))
    
    todas_distancias = [h["pos"] for t in trayectorias.values() for h in t["posiciones"]]
    ymin, ymax = (min(todas_distancias), max(todas_distancias)) if todas_distancias else (0, 100)
    
    aviones_ids = [
        num for num, t in trayectorias.items()
        if any(h["minuto"] in minutos for h in t["posiciones"])
    ]
    aviones_ids = sorted(aviones_ids)
    
    colores = {
        "en_vuelo": "blue",
        "marcha_atras": "orange",
        "aterrizado": "green",
        "desviado": "red"
    }
    
    fig, axes = plt.subplots(1, cantidad, figsize=(4*cantidad, 6), sharey=True)
    if cantidad == 1:
        axes = [axes]
    
    for ax, minuto in zip(axes, minutos):
        etiquetas_usadas = set()
        
        for num in aviones_ids:
            t = trayectorias[num]
            registro = next((h for h in t["posiciones"] if h["minuto"] == minuto), None)
            if registro is None:
                continue
            
            distancia = registro["pos"]
            vel = registro["vel"]
            estado = registro["estado"]
            gap_a = registro.get("gap_adelante", None)
            gap_t = registro.get("gap_atras", None)
            lead = registro.get("lead_id", None)
            tail = registro.get("tail_id", None)
            
            color = colores.get(estado, "gray")
            lbl = estado if estado not in etiquetas_usadas else None
            if lbl:
                etiquetas_usadas.add(estado)
            
            ax.scatter(num, distancia, color=color, label=lbl, s=60, zorder=3)
            # mostrar información extra con 2 cifras significativas para gaps
            gap_a_str = f"{gap_a:.2f}" if gap_a is not None else "None"
            gap_t_str = f"{gap_t:.2f}" if gap_t is not None else "None"
            info = f"{vel:.0f} kt\nG.A:{gap_a_str}\nG.T:{gap_t_str}\nL:{lead}\nT:{tail}"
            ax.text(num, distancia, info, fontsize=8, ha="left", va="bottom")
        
        ax.set_title(f"Minuto {minuto}")
        ax.set_xticks(aviones_ids)
        ax.set_xticklabels(aviones_ids, rotation=45)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.set_ylim(ymax, ymin)  # invertir eje Y
        
        for y, lbl in [(50, "50 nm"), (15, "15 nm"), (5, "5 nm")]:
            ax.axhline(y=y, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    
    axes[0].set_ylabel("Distancia a AEP (nm)")
    fig.text(0.5, 0.04, "Avión (ID)", ha="center")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right")
    plt.suptitle("Estados de aviones en minutos consecutivos (gaps con 2 cifras significativas)")
    plt.tight_layout(rect=[0, 0, 0.95, 0.95])
    plt.show()


def debug_avion(avion_num, resultados):
    """
    Muestra minuto a minuto el estado, velocidad y gaps de un avión específico.
    """
    t = resultados['trayectorias'].get(avion_num)
    if not t:
        print(f"No hay datos del avión {avion_num}")
        return
    
    print(f"DEBUG Avión {avion_num}")
    # Header
    print("Min | Pos(nm) | Vel(kt) | GapA(min) | Lead | GapT(min) | Tail |     Estado")
    print("-"*75)

    # Rows
    for rec in t['posiciones']:
        minuto = rec['minuto']
        pos = rec['pos']
        vel = rec['vel']
        gap_a = rec['gap_adelante']
        lead = rec['lead_id']
        gap_t = rec.get('gap_atras', None)
        tail = rec.get('tail_id', None)
        estado = rec['estado']

        print(
            f"{minuto:4} | "
            f"{pos:7.1f} | "
            f"{vel:7.1f} | "
            f"{(f'{gap_a:7.2f}' if gap_a is not None else '   None')} | "
            f"{str(lead):>4} | "
            f"{(f'{gap_t:7.2f}' if gap_t is not None else '   None')} | "
            f"{str(tail):>4} | "
            f"{estado:>10}"
        )




