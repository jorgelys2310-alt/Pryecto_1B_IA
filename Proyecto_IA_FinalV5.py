"""
Proyecto IA - Optimizador de horarios
CSP + búsqueda local

Descripción:
Sistema de generación y optimización de horarios académicos utilizando
técnicas de Inteligencia Artificial.

El programa modela el problema como un CSP (Constraint Satisfaction Problem)
y aplica algoritmos de búsqueda local para mejorar la calidad del horario.

Técnicas implementadas:
- CSP con Backtracking
- MRV (Minimum Remaining Values)
- Hill Climbing
- Random Restart
- Simulated Annealing
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import copy
import math
import time
import csv
from typing import Dict, List, Tuple, Optional

# Datos base del horario

# Horas disponibles. Cada clase dura 2 horas.
HORARIO_BASE = {
    "Lunes": ["7AM", "9AM", "11AM", "2PM"],
    "Martes": ["9AM", "11AM", "3PM", "5PM"],
    "Miercoles": ["7AM", "9AM", "3PM", "5PM"],
    "Jueves": ["7AM", "11AM", "2PM", "4PM"],
    "Viernes": ["7AM", "9AM", "11AM", "3PM"],
}

# Lista de días utilizados en el sistema.
DIAS = list(HORARIO_BASE.keys())
# Todas las horas posibles del horario.
TODAS_LAS_HORAS = ["7AM", "9AM", "11AM", "2PM", "3PM", "4PM", "5PM"]
# Todas las horas posibles del horario.
DURACION_CLASE = 2

# Valor numerico de cada hora para revisar cruces.
HORA_INICIO = {
    "7AM": 7,
    "9AM": 9,
    "11AM": 11,
    "2PM": 14,
    "3PM": 15,
    "4PM": 16,
    "5PM": 17,
}

# Sesiones semanales por materia.
SESIONES_MATERIA = {
    "Programacion": 3,
    "Fisica": 2,
    "Matematicas": 2,
    "Redes": 2,
    "Base de Datos": 3,
}

# Estudiantes por materia para validar la capacidad del aula.
ESTUDIANTES_MATERIA = {
    "Programacion": 22,
    "Fisica": 18,
    "Matematicas": 28,
    "Redes": 20,
    "Base de Datos": 24,
}

# Lista de aulas disponibles.
AULAS = ["Aula1", "Aula2", "Lab1", "Lab2"]
# Capacidad máxima por aula.
CAPACIDAD_AULA = {
    "Aula1": 20,
    "Aula2": 30,
    "Lab1": 25,
    "Lab2": 20,
}

# Conjunto de aulas bloqueadas manualmente.
# Formato:
# (aula, dia, hora)
AULAS_NO_DISPONIBLES = set()

# Materias que puede dictar cada profesor.
MATERIAS_PROFESOR = {
    "Juan": ["Programacion", "Redes"],
    "Ana": ["Matematicas"],
    "Carlos": ["Fisica"],
    "Luis": ["Base de Datos"],
}

# Profesor fijo para cada materia.
PROFESOR_MATERIA = {}
for profesor, materias in MATERIAS_PROFESOR.items():
    for materia in materias:
        PROFESOR_MATERIA[materia] = profesor

# Horarios donde el profesor no esta disponible.
RESTRICCIONES_PROFESOR = {
    "Juan": {("Viernes", "9AM")},
    "Ana": {("Martes", "11AM")},
    "Carlos": {("Lunes", "7AM"), ("Miercoles", "5PM")},
    "Luis": {("Jueves", "2PM")},
}

# Restricciones blandas:
# se penalizan en la función objetivo.
HORAS_TEMPRANAS = {"7AM"}
HORAS_TARDE_VIERNES = {"3PM", "5PM"}
AULAS_PREFERIDAS = {
    "Programacion": ["Lab1", "Lab2"],
    "Base de Datos": ["Lab1", "Lab2"],
    "Redes": ["Lab1"],
}

# Pesos utilizados para calcular penalizaciones.
PESOS = {
    "temprano": 3,
    "viernes_tarde": 5,
    "aula_no_preferida": 2,
    "huecos": 3,
    "distribucion": 3,
}

# Funciones generales

def hora_fin(hora: str) -> int:
    """
    Retorna la hora final de una clase
    sumando la duración establecida.
    """
    return HORA_INICIO[hora] + DURACION_CLASE


def se_cruzan(hora1: str, hora2: str) -> bool:
    """
    Determina si dos bloques horarios se cruzan.
    """
    inicio1 = HORA_INICIO[hora1]
    fin1 = hora_fin(hora1)
    inicio2 = HORA_INICIO[hora2]
    fin2 = hora_fin(hora2)
    return inicio1 < fin2 and inicio2 < fin1


def toca_almuerzo(hora: str) -> bool:
    """
    Verifica si una clase invade el bloque de almuerzo.
    """
    # Bloque de almuerzo: de 1PM a 2PM.
    inicio = HORA_INICIO[hora]
    fin = hora_fin(hora)
    return inicio < 14 and 13 < fin


def generar_variables() -> List[Tuple[str, int]]:
    """
    Genera las variables del CSP.

    Cada variable representa:
    (materia, número de sesión)
    """
    variables = []
    for materia, sesiones in SESIONES_MATERIA.items():
        for num in range(1, sesiones + 1):
            variables.append((materia, num))
    return variables


def profesor_esta_capacitado(profesor: str, materia: str) -> bool:
    """
    Verifica si un profesor puede dictar una materia.
    """
    return materia in MATERIAS_PROFESOR.get(profesor, [])


def profesor_disponible(profesor: str, dia: str, hora: str) -> bool:
    """
    Verifica disponibilidad del profesor
    considerando posibles cruces horarios.
    """
    for dia_bloq, hora_bloq in RESTRICCIONES_PROFESOR.get(profesor, set()):
        if dia_bloq == dia and se_cruzan(hora, hora_bloq):
            return False
    return True


def aula_disponible(aula: str, dia: str, hora: str) -> bool:
    """
    Verifica si un aula está disponible.
    """
    for aula_bloq, dia_bloq, hora_bloq in AULAS_NO_DISPONIBLES:
        if aula_bloq == aula and dia_bloq == dia and se_cruzan(hora, hora_bloq):
            return False
    return True


def generar_dominio(variable: Tuple[str, int]) -> List[Tuple[str, str, str]]:
    """
    Genera el dominio válido para una variable.

    Cada valor posible tiene la forma:
    (dia, hora, aula)
    """
    materia, _ = variable
    profesor = PROFESOR_MATERIA[materia]
    dominio = []

    for dia, horas in HORARIO_BASE.items():
        for hora in horas:
            if not profesor_disponible(profesor, dia, hora):
                continue
            if toca_almuerzo(hora):
                continue

            for aula in AULAS:
                if CAPACIDAD_AULA[aula] < ESTUDIANTES_MATERIA[materia]:
                    continue
                if not aula_disponible(aula, dia, hora):
                    continue
                dominio.append((dia, hora, aula))

    return dominio

# Restricciones obligatorias

    """
    Verifica todas las restricciones duras del CSP.

    Restricciones evaluadas:
    - Profesor capacitado.
    - Disponibilidad del profesor.
    - Capacidad del aula.
    - Aula disponible.
    - Sin cruces de horario.
    - Sin repetición de materia el mismo día.
    - Sin clases en almuerzo.

    Retorna True si la asignación es válida.
    """
def cumple_restricciones_duras(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]],
                            variable: Tuple[str, int],
                            valor: Tuple[str, str, str]) -> bool:
    materia, _ = variable
    dia_nuevo, hora_nueva, aula_nueva = valor
    profesor_nuevo = PROFESOR_MATERIA.get(materia)

    if profesor_nuevo is None:
        return False

    # Profesor correcto para la materia.
    if not profesor_esta_capacitado(profesor_nuevo, materia):
        return False

    # Disponibilidad del profesor.
    if not profesor_disponible(profesor_nuevo, dia_nuevo, hora_nueva):
        return False

    # No se asignan clases en la hora de almuerzo.
    if toca_almuerzo(hora_nueva):
        return False

    # Capacidad y disponibilidad del aula.
    if CAPACIDAD_AULA[aula_nueva] < ESTUDIANTES_MATERIA[materia]:
        return False
    if not aula_disponible(aula_nueva, dia_nuevo, hora_nueva):
        return False

    for (materia_asig, _), (dia_asig, hora_asig, aula_asig) in asignacion.items():
        profesor_asig = PROFESOR_MATERIA[materia_asig]

        if dia_asig != dia_nuevo:
            continue

        # Una materia no se repite el mismo dia.
        if materia_asig == materia:
            return False

        # Como es un solo curso, no puede tener dos clases al mismo tiempo.
        if se_cruzan(hora_asig, hora_nueva):
            return False

        # Reglas para evitar cruces de profesor y aula.
        if aula_asig == aula_nueva and se_cruzan(hora_asig, hora_nueva):
            return False

        if profesor_asig == profesor_nuevo and se_cruzan(hora_asig, hora_nueva):
            return False

    return True

    """
    Revisa todas las restricciones duras
    sobre una solución completa y devuelve
    una lista de errores encontrados.
    """
def revisar_restricciones_duras(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]]) -> List[str]:
    errores = []
    items = list(asignacion.items())

    for variable, valor in items:
        materia, _ = variable
        dia, hora, aula = valor
        profesor = PROFESOR_MATERIA.get(materia)

        if profesor is None or not profesor_esta_capacitado(profesor, materia):
            errores.append(f"Profesor no capacitado para {materia}")
        if profesor and not profesor_disponible(profesor, dia, hora):
            errores.append(f"{profesor} no disponible {dia} {hora}")
        if toca_almuerzo(hora):
            errores.append(f"Clase en hora de almuerzo: {materia}")
        if CAPACIDAD_AULA[aula] < ESTUDIANTES_MATERIA[materia]:
            errores.append(f"Capacidad insuficiente: {materia} en {aula}")
        if not aula_disponible(aula, dia, hora):
            errores.append(f"Aula no disponible: {aula} {dia} {hora}")

    for i in range(len(items)):
        (mat1, _), (dia1, hora1, aula1) = items[i]
        prof1 = PROFESOR_MATERIA[mat1]
        for j in range(i + 1, len(items)):
            (mat2, _), (dia2, hora2, aula2) = items[j]
            prof2 = PROFESOR_MATERIA[mat2]

            if dia1 != dia2:
                continue

            if mat1 == mat2:
                errores.append(f"{mat1} repetida el mismo dia")
            if se_cruzan(hora1, hora2):
                errores.append(f"Cruce de grupo: {dia1} {hora1}-{hora2}")
            if aula1 == aula2 and se_cruzan(hora1, hora2):
                errores.append(f"Cruce de aula: {aula1} {dia1}")
            if prof1 == prof2 and se_cruzan(hora1, hora2):
                errores.append(f"Cruce de profesor: {prof1} {dia1}")

    for materia, sesiones in SESIONES_MATERIA.items():
        total = sum(1 for (mat, _) in asignacion if mat == materia)
        if total != sesiones:
            errores.append(f"Sesiones incompletas en {materia}")
        if not (1 <= sesiones <= 3):
            errores.append(f"Numero de sesiones fuera de rango en {materia}")

    return errores

# Solucion inicial
    """
    Algoritmo CSP basado en Backtracking.

    Busca una solución válida asignando valores
    a las variables de manera recursiva.

    Utiliza la heurística MRV
    (Minimum Remaining Values) para escoger
    primero la variable con menos opciones válidas.
    """
def backtracking(variables: List[Tuple[str, int]],
                asignacion: Optional[Dict[Tuple[str, int], Tuple[str, str, str]]] = None,
                dominios: Optional[Dict[Tuple[str, int], List[Tuple[str, str, str]]]] = None,
                aleatorio: bool = True) -> Optional[Dict[Tuple[str, int], Tuple[str, str, str]]]:
    if asignacion is None:
        asignacion = {}
    if dominios is None:
        dominios = {variable: generar_dominio(variable) for variable in variables}

    if len(asignacion) == len(variables):
        return copy.deepcopy(asignacion)

    sin_asignar = [variable for variable in variables if variable not in asignacion]

    # MRV: primero se toma la sesion con menos opciones.
    variable = min(
        sin_asignar,
        key=lambda v: sum(1 for valor in dominios[v]
                        if cumple_restricciones_duras(asignacion, v, valor))
    )

    dominio = dominios[variable][:]
    if aleatorio:
        random.shuffle(dominio)

    for valor in dominio:
        if cumple_restricciones_duras(asignacion, variable, valor):
            asignacion[variable] = valor
            resultado = backtracking(variables, asignacion, dominios, aleatorio)
            if resultado is not None:
                return resultado
            del asignacion[variable]

    return None

# Puntaje del horario
    """
    Calcula penalizaciones por huecos
    entre clases del grupo.
    """
def calcular_huecos_grupo(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]]) -> int:
    penalizacion = 0

    for dia in DIAS:
        horas_dia = []
        for _, (dia_asig, hora, _) in asignacion.items():
            if dia_asig == dia:
                horas_dia.append(hora)

        horas_dia = sorted(horas_dia, key=lambda h: HORA_INICIO[h])

        for i in range(len(horas_dia) - 1):
            fin_actual = hora_fin(horas_dia[i])
            inicio_siguiente = HORA_INICIO[horas_dia[i + 1]]
            hueco = inicio_siguiente - fin_actual
            if hueco > 0:
                penalizacion += hueco * PESOS["huecos"]

    return penalizacion

    """
    Función objetivo del problema.

    Calcula un puntaje de calidad del horario
    considerando restricciones blandas.

    Mientras mayor sea el puntaje,
    mejor es la solución.
    """
def calcular_calidad(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]]) -> Tuple[int, Dict[str, str]]:
    puntaje = 100
    desglose = {}

    clases_tempranas = sum(1 for _, hora, _ in asignacion.values() if hora in HORAS_TEMPRANAS)
    pen_temprano = clases_tempranas * PESOS["temprano"]
    puntaje -= pen_temprano
    desglose["RB1 Evitar 7AM"] = f"{clases_tempranas} clase(s), -{pen_temprano} pts"

    viernes_tarde = sum(1 for dia, hora, _ in asignacion.values()
                         if dia == "Viernes" and hora in HORAS_TARDE_VIERNES)
    pen_viernes = viernes_tarde * PESOS["viernes_tarde"]
    puntaje -= pen_viernes
    desglose["RB2 Evitar viernes tarde"] = f"{viernes_tarde} clase(s), -{pen_viernes} pts"

    no_preferidas = 0
    for (materia, _), (_, _, aula) in asignacion.items():
        if materia in AULAS_PREFERIDAS and aula not in AULAS_PREFERIDAS[materia]:
            no_preferidas += 1
    pen_aulas = no_preferidas * PESOS["aula_no_preferida"]
    puntaje -= pen_aulas
    desglose["RB3 Aulas preferidas"] = f"{no_preferidas} no preferida(s), -{pen_aulas} pts"

    pen_huecos = calcular_huecos_grupo(asignacion)
    puntaje -= pen_huecos
    desglose["RB4 Huecos del grupo"] = f"-{pen_huecos} pts"

    conteo_dia = {dia: 0 for dia in DIAS}
    for dia, _, _ in asignacion.values():
        conteo_dia[dia] += 1

    ideal = len(asignacion) / len(DIAS)
    diferencia = sum(abs(conteo_dia[dia] - ideal) for dia in DIAS)
    pen_dist = int(diferencia * PESOS["distribucion"])
    puntaje -= pen_dist
    resumen_dias = ", ".join(f"{dia[:3]}:{conteo_dia[dia]}" for dia in DIAS)
    desglose["RB5 Distribucion semanal"] = f"-{pen_dist} pts ({resumen_dias})"

    puntaje = max(0, min(100, puntaje))
    desglose["_total"] = str(puntaje)
    return puntaje, desglose

# Cambios para buscar mejoras
    """
    Verifica si una solución completa
    cumple todas las restricciones duras.
    """
def solucion_valida(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]],
                    variables: List[Tuple[str, int]]) -> bool:
    if len(asignacion) != len(variables):
        return False

    parcial = {}
    for variable in variables:
        if variable not in asignacion:
            return False
        valor = asignacion[variable]
        if not cumple_restricciones_duras(parcial, variable, valor):
            return False
        parcial[variable] = valor

    return True

    """
    Genera soluciones vecinas para búsqueda local.

    Movimientos utilizados:
    - mover una clase,
    - intercambiar dos clases.
    """
def generar_vecinos(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]],
                    variables: List[Tuple[str, int]],
                    max_vecinos: int = 60) -> List[Dict[Tuple[str, int], Tuple[str, str, str]]]:
    vecinos = []
    claves = list(asignacion.keys())

    # Movimiento 1: mover una clase.
    intentos = claves[:]
    random.shuffle(intentos)

    for variable in intentos:
        dominio = generar_dominio(variable)
        random.shuffle(dominio)
        base = dict(asignacion)
        del base[variable]

        for valor in dominio[:20]:
            if valor == asignacion[variable]:
                continue
            if cumple_restricciones_duras(base, variable, valor):
                nuevo = dict(asignacion)
                nuevo[variable] = valor
                vecinos.append(nuevo)
                if len(vecinos) >= max_vecinos:
                    return vecinos

    # Movimiento 2: intercambiar dos clases.
    pares = []
    for i in range(len(claves)):
        for j in range(i + 1, len(claves)):
            pares.append((claves[i], claves[j]))
    random.shuffle(pares)

    for v1, v2 in pares:
        valor1 = asignacion[v1]
        valor2 = asignacion[v2]
        base = dict(asignacion)
        del base[v1]
        del base[v2]

        if cumple_restricciones_duras(base, v1, valor2):
            base[v1] = valor2
            if cumple_restricciones_duras(base, v2, valor1):
                nuevo = dict(asignacion)
                nuevo[v1] = valor2
                nuevo[v2] = valor1
                vecinos.append(nuevo)
                if len(vecinos) >= max_vecinos:
                    return vecinos

    return vecinos

# Mejora del horario
    """
    Optimiza una solución usando Hill Climbing.

    El algoritmo busca vecinos con mejor puntaje
    hasta alcanzar un óptimo local.

    Implementa Random Restart para escapar
    de óptimos locales.
    """
def hill_climbing(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]],
                  variables: List[Tuple[str, int]],
                  max_iter: int = 300,
                  reinicios: int = 4) -> Tuple[Dict[Tuple[str, int], Tuple[str, str, str]], List[int]]:
    mejor_global = copy.deepcopy(asignacion)
    mejor_puntaje_global, _ = calcular_calidad(mejor_global)
    historial = [mejor_puntaje_global]

    for intento in range(reinicios + 1):
        if intento == 0:
            actual = copy.deepcopy(asignacion)
        else:
            nuevo_inicio = backtracking(variables, aleatorio=True)
            if nuevo_inicio is None:
                continue
            actual = nuevo_inicio

        puntaje_actual, _ = calcular_calidad(actual)

        for _ in range(max_iter):
            vecinos = generar_vecinos(actual, variables)
            if not vecinos:
                break

            mejor_vecino = None
            mejor_puntaje_vecino = puntaje_actual

            for vecino in vecinos:
                puntaje_vecino, _ = calcular_calidad(vecino)
                if puntaje_vecino > mejor_puntaje_vecino:
                    mejor_vecino = vecino
                    mejor_puntaje_vecino = puntaje_vecino

            if mejor_vecino is None:
                break

            actual = mejor_vecino
            puntaje_actual = mejor_puntaje_vecino
            historial.append(puntaje_actual)

        if puntaje_actual > mejor_puntaje_global:
            mejor_global = copy.deepcopy(actual)
            mejor_puntaje_global = puntaje_actual

    return mejor_global, historial

    """
    Optimiza una solución usando Simulated Annealing.

    Permite aceptar temporalmente soluciones peores
    con cierta probabilidad para evitar
    quedar atrapado en óptimos locales.
    """
def simulated_annealing(asignacion: Dict[Tuple[str, int], Tuple[str, str, str]],
                        variables: List[Tuple[str, int]],
                        max_iter: int = 800,
                        temp_inicial: float = 18.0,
                        enfriamiento: float = 0.992) -> Tuple[Dict[Tuple[str, int], Tuple[str, str, str]], List[int]]:
    actual = copy.deepcopy(asignacion)
    puntaje_actual, _ = calcular_calidad(actual)

    mejor = copy.deepcopy(actual)
    mejor_puntaje = puntaje_actual
    historial = [puntaje_actual]

    temperatura = temp_inicial

    for _ in range(max_iter):
        temperatura *= enfriamiento
        if temperatura < 0.01:
            break

        vecinos = generar_vecinos(actual, variables, max_vecinos=30)
        if not vecinos:
            break

        vecino = random.choice(vecinos)
        puntaje_vecino, _ = calcular_calidad(vecino)
        diferencia = puntaje_vecino - puntaje_actual

        if diferencia > 0:
            aceptar = True
        else:
            aceptar = random.random() < math.exp(diferencia / temperatura)

        if aceptar:
            actual = vecino
            puntaje_actual = puntaje_vecino

        if puntaje_actual > mejor_puntaje:
            mejor = copy.deepcopy(actual)
            mejor_puntaje = puntaje_actual

        historial.append(mejor_puntaje)

    return mejor, historial

# Pantalla principal
C = {
    "fondo": "#1e1e2e",
    "panel": "#313244",
    "panel2": "#45475a",
    "oscuro": "#181825",
    "texto": "#cdd6f4",
    "texto2": "#a6adc8",
    "azul": "#89b4fa",
    "verde": "#a6e3a1",
    "amarillo": "#f9e2af",
    "naranja": "#fab387",
    "rojo": "#f38ba8",
    "morado": "#cba6f7",
}

COLOR_MATERIA = {
    "Programacion": C["azul"],
    "Fisica": C["naranja"],
    "Matematicas": C["verde"],
    "Redes": C["amarillo"],
    "Base de Datos": C["morado"],
}

COLORES_EXTRA = [C["azul"], C["verde"], C["amarillo"], C["naranja"], C["rojo"], C["morado"]]


def asignar_color_materia(materia: str):
    # Color para materias que se agreguen despues.
    if materia not in COLOR_MATERIA:
        COLOR_MATERIA[materia] = COLORES_EXTRA[len(COLOR_MATERIA) % len(COLORES_EXTRA)]

# Clase principal de la interfaz gráfica.
# Controla generación, optimización,
# visualización y validación del horario.
class OptimizerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Optimizador de horarios - CSP")
        self.root.geometry("1450x840")
        self.root.configure(bg=C["fondo"])
        self.root.resizable(True, True)

        self.variables = generar_variables()
        self.solucion_inicial = None
        self.solucion_actual = None
        self.puntaje_inicial = None

        self.configurar_estilos()
        self.construir_interfaz()

    def configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=C["panel"],
            background=C["panel"],
            foreground=C["texto"],
            selectbackground=C["azul"],
            selectforeground=C["oscuro"],
        )
        style.map("TCombobox", fieldbackground=[("readonly", C["panel"])])

    def boton(self, parent, texto, comando, color):
        return tk.Button(
            parent,
            text=texto,
            command=comando,
            bg=color,
            fg=C["oscuro"],
            font=("Consolas", 9, "bold"),
            relief="flat",
            padx=6,
            pady=5,
            cursor="hand2",
            activebackground=color,
            activeforeground=C["oscuro"],
        )

    def construir_interfaz(self):
        barra = tk.Frame(self.root, bg=C["panel"], height=56)
        barra.pack(fill="x")
        barra.pack_propagate(False)

        tk.Label(
            barra,
            text="Optimizador de horarios",
            font=("Consolas", 15, "bold"),
            bg=C["panel"],
            fg=C["azul"],
        ).pack(side="left", padx=20, pady=10)

        tk.Label(
            barra,
            text="CSP | Backtracking | Hill Climbing | SA",
            font=("Consolas", 9),
            bg=C["panel"],
            fg=C["texto2"],
        ).pack(side="left", pady=18)

        botones = tk.Frame(barra, bg=C["panel"])
        botones.pack(side="right", padx=12)

        self.boton(botones, "Generar", self.generar_inicial, C["azul"]).pack(side="left", padx=3)
        self.boton(botones, "Hill", self.optimizar_hc, C["verde"]).pack(side="left", padx=3)
        self.boton(botones, "Annealing", self.optimizar_sa, C["naranja"]).pack(side="left", padx=3)
        self.boton(botones, "+ Materia", self.agregar_materia, C["amarillo"]).pack(side="left", padx=3)
        self.boton(botones, "+ Restriccion", self.agregar_restriccion, C["rojo"]).pack(side="left", padx=3)
        self.boton(botones, "CSV", self.exportar_csv, C["morado"]).pack(side="left", padx=3)
        self.boton(botones, "Reiniciar", self.reiniciar, C["panel2"]).pack(side="left", padx=3)

        contenido = tk.Frame(self.root, bg=C["fondo"])
        contenido.pack(fill="both", expand=True, padx=8, pady=8)

        izquierda = tk.Frame(contenido, bg=C["fondo"])
        izquierda.pack(side="left", fill="both", expand=True)

        tk.Label(
            izquierda,
            text="Horario generado",
            font=("Consolas", 11, "bold"),
            bg=C["fondo"],
            fg=C["texto"],
        ).pack(anchor="w", pady=(0, 4))

        self.tabla_frame = tk.Frame(izquierda, bg=C["fondo"])
        self.tabla_frame.pack(fill="both", expand=True)
        self.construir_tabla_vacia()

        derecha = tk.Frame(contenido, bg=C["fondo"], width=320)
        derecha.pack(side="right", fill="y", padx=(10, 0))
        derecha.pack_propagate(False)

        self.panel_puntaje(derecha)
        self.panel_comparacion(derecha)
        self.panel_validacion(derecha)
        self.panel_restricciones(derecha)
        self.panel_log(derecha)

        self.status_var = tk.StringVar(value="Listo. Genera una solucion para empezar.")
        tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=C["oscuro"],
            fg=C["texto2"],
            font=("Consolas", 9),
            anchor="w",
            padx=10,
        ).pack(fill="x", side="bottom")

    def panel_puntaje(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="x", pady=(0, 8))

        tk.Label(
            f,
            text="Puntaje de calidad",
            font=("Consolas", 10, "bold"),
            bg=C["panel"],
            fg=C["texto2"],
        ).pack(pady=(8, 2))

        self.puntaje_label = tk.Label(
            f,
            text="-",
            font=("Consolas", 32, "bold"),
            bg=C["panel"],
            fg=C["azul"],
        )
        self.puntaje_label.pack()

        self.desglose_text = tk.Text(
            f,
            height=8,
            bg=C["oscuro"],
            fg=C["texto"],
            font=("Consolas", 8),
            relief="flat",
            padx=8,
            pady=4,
            state="disabled",
        )
        self.desglose_text.pack(fill="x", padx=8, pady=(4, 8))

    def panel_comparacion(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="x", pady=(0, 8))

        tk.Label(
            f,
            text="Comparacion",
            font=("Consolas", 10, "bold"),
            bg=C["panel"],
            fg=C["texto2"],
        ).pack(anchor="w", padx=8, pady=(8, 2))

        self.comp_label = tk.Label(
            f,
            text="Sin datos todavia",
            font=("Consolas", 9),
            bg=C["panel"],
            fg=C["texto2"],
            justify="left",
            padx=8,
            pady=4,
        )
        self.comp_label.pack(anchor="w", pady=(0, 8))

    def panel_validacion(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="x", pady=(0, 8))

        tk.Label(
            f,
            text="Validacion",
            font=("Consolas", 10, "bold"),
            bg=C["panel"],
            fg=C["texto2"],
        ).pack(anchor="w", padx=8, pady=(8, 2))

        self.validacion_label = tk.Label(
            f,
            text="Restricciones duras: -",
            font=("Consolas", 9),
            bg=C["panel"],
            fg=C["texto2"],
            justify="left",
            padx=8,
            pady=4,
        )
        self.validacion_label.pack(anchor="w", pady=(0, 8))

    def panel_restricciones(self, parent):
        tk.Label(
            parent,
            text="Restricciones activas",
            font=("Consolas", 10, "bold"),
            bg=C["fondo"],
            fg=C["texto2"],
        ).pack(anchor="w", pady=(0, 2))

        self.restricciones_text = tk.Text(
            parent,
            height=13,
            bg=C["panel"],
            fg=C["verde"],
            font=("Consolas", 8),
            relief="flat",
            padx=8,
            pady=4,
            state="disabled",
        )
        self.restricciones_text.pack(fill="x")
        self.refrescar_restricciones()

    def panel_log(self, parent):
        tk.Label(
            parent,
            text="Log",
            font=("Consolas", 10, "bold"),
            bg=C["fondo"],
            fg=C["texto2"],
        ).pack(anchor="w", pady=(8, 2))

        self.log_text = tk.Text(
            parent,
            height=7,
            bg=C["panel"],
            fg=C["texto"],
            font=("Consolas", 8),
            relief="flat",
            padx=8,
            pady=4,
            state="disabled",
        )
        self.log_text.pack(fill="both", expand=True)

    def construir_tabla_vacia(self):
        for widget in self.tabla_frame.winfo_children():
            widget.destroy()

        tk.Label(
            self.tabla_frame,
            text="",
            width=7,
            bg=C["panel"],
            font=("Consolas", 9, "bold"),
        ).grid(row=0, column=0, padx=1, pady=1, sticky="nsew")

        for col, dia in enumerate(DIAS):
            tk.Label(
                self.tabla_frame,
                text=dia,
                bg=C["panel2"],
                fg=C["texto"],
                font=("Consolas", 9, "bold"),
                width=20,
                pady=6,
            ).grid(row=0, column=col + 1, padx=1, pady=1, sticky="nsew")

        for fila, hora in enumerate(TODAS_LAS_HORAS):
            tk.Label(
                self.tabla_frame,
                text=hora,
                bg=C["panel2"],
                fg=C["texto2"],
                font=("Consolas", 9),
                width=7,
                pady=8,
            ).grid(row=fila + 1, column=0, padx=1, pady=1, sticky="nsew")

            for col, dia in enumerate(DIAS):
                disponible = hora in HORARIO_BASE.get(dia, [])
                texto = "" if disponible else "-"
                fondo = C["fondo"] if disponible else C["oscuro"]

                tk.Label(
                    self.tabla_frame,
                    text=texto,
                    bg=fondo,
                    fg=C["texto2"],
                    font=("Consolas", 8),
                    width=20,
                    pady=8,
                ).grid(row=fila + 1, column=col + 1, padx=1, pady=1, sticky="nsew")

        for i in range(len(DIAS) + 1):
            self.tabla_frame.columnconfigure(i, weight=1)

    def mostrar_solucion(self, solucion):
        celdas = {}
        for (materia, num), (dia, hora, aula) in solucion.items():
            profesor = PROFESOR_MATERIA[materia]
            texto = f"{materia}\n{aula} | {profesor}"
            celdas[(dia, hora)] = (texto, materia)

        for widget in self.tabla_frame.winfo_children():
            widget.destroy()

        tk.Label(self.tabla_frame, text="", width=7, bg=C["panel"]).grid(row=0, column=0, padx=1, pady=1, sticky="nsew")

        for col, dia in enumerate(DIAS):
            tk.Label(
                self.tabla_frame,
                text=dia,
                bg=C["panel2"],
                fg=C["texto"],
                font=("Consolas", 9, "bold"),
                width=20,
                pady=6,
            ).grid(row=0, column=col + 1, padx=1, pady=1, sticky="nsew")

        for fila, hora in enumerate(TODAS_LAS_HORAS):
            tk.Label(
                self.tabla_frame,
                text=hora,
                bg=C["panel2"],
                fg=C["texto2"],
                font=("Consolas", 9),
                width=7,
                pady=8,
            ).grid(row=fila + 1, column=0, padx=1, pady=1, sticky="nsew")

            for col, dia in enumerate(DIAS):
                disponible = hora in HORARIO_BASE.get(dia, [])
                if not disponible:
                    tk.Label(
                        self.tabla_frame,
                        text="-",
                        bg=C["oscuro"],
                        fg=C["texto2"],
                        font=("Consolas", 8),
                        width=20,
                        pady=8,
                    ).grid(row=fila + 1, column=col + 1, padx=1, pady=1, sticky="nsew")
                    continue

                if (dia, hora) in celdas:
                    texto, materia = celdas[(dia, hora)]
                    tk.Label(
                        self.tabla_frame,
                        text=texto,
                        bg=COLOR_MATERIA.get(materia, C["azul"]),
                        fg=C["oscuro"],
                        font=("Consolas", 8, "bold"),
                        width=20,
                        pady=5,
                        wraplength=145,
                        justify="center",
                    ).grid(row=fila + 1, column=col + 1, padx=1, pady=1, sticky="nsew")
                else:
                    tk.Label(
                        self.tabla_frame,
                        text="",
                        bg=C["fondo"],
                        fg=C["texto2"],
                        font=("Consolas", 8),
                        width=20,
                        pady=8,
                    ).grid(row=fila + 1, column=col + 1, padx=1, pady=1, sticky="nsew")

        for i in range(len(DIAS) + 1):
            self.tabla_frame.columnconfigure(i, weight=1)

    def actualizar_puntaje(self, solucion):
        puntaje, desglose = calcular_calidad(solucion)
        color = C["verde"] if puntaje >= 85 else C["amarillo"] if puntaje >= 65 else C["rojo"]
        self.puntaje_label.config(text=str(puntaje), fg=color)

        self.desglose_text.config(state="normal")
        self.desglose_text.delete("1.0", "end")
        for nombre, valor in desglose.items():
            if nombre != "_total":
                self.desglose_text.insert("end", f"{nombre}:\n  {valor}\n\n")
        self.desglose_text.config(state="disabled")
        return puntaje

    def actualizar_comparacion(self, puntaje_actual):
        if self.puntaje_inicial is None:
            return
        diferencia = puntaje_actual - self.puntaje_inicial
        signo = "+" if diferencia >= 0 else ""
        color = C["verde"] if diferencia > 0 else C["rojo"] if diferencia < 0 else C["texto2"]
        self.comp_label.config(
            text=f"Inicial: {self.puntaje_inicial} pts\nActual:  {puntaje_actual} pts\nMejora:  {signo}{diferencia} pts",
            fg=color,
        )

    def actualizar_validacion(self, solucion):
        errores = revisar_restricciones_duras(solucion)
        asignadas = len(solucion)
        total = len(self.variables)

        if not errores:
            texto = f"Restricciones duras violadas: 0\nSesiones asignadas: {asignadas}/{total}"
            color = C["verde"]
        else:
            texto = f"Restricciones duras violadas: {len(errores)}\n" + "\n".join(errores[:3])
            color = C["rojo"]

        self.validacion_label.config(text=texto, fg=color)

    def refrescar_restricciones(self):
        self.restricciones_text.config(state="normal")
        self.restricciones_text.delete("1.0", "end")
        self.restricciones_text.insert("end", "Profesores no disponibles:\n")

        for profesor, restricciones in RESTRICCIONES_PROFESOR.items():
            for dia, hora in sorted(restricciones):
                self.restricciones_text.insert("end", f"{profesor}: {dia} {hora}\n")

        if AULAS_NO_DISPONIBLES:
            self.restricciones_text.insert("end", "\nAulas no disponibles:\n")
            for aula, dia, hora in sorted(AULAS_NO_DISPONIBLES):
                self.restricciones_text.insert("end", f"{aula}: {dia} {hora}\n")

        self.restricciones_text.insert("end", "\nMaterias activas:\n")
        for materia, sesiones in SESIONES_MATERIA.items():
            profesor = PROFESOR_MATERIA.get(materia, "-")
            self.restricciones_text.insert("end", f"{materia}: {sesiones} ses. | {profesor}\n")

        self.restricciones_text.config(state="disabled")

    def log(self, mensaje, color=None):
        self.log_text.config(state="normal")
        tag = f"tag_{time.time()}"
        self.log_text.insert("end", f"- {mensaje}\n", tag)
        if color:
            self.log_text.tag_config(tag, foreground=color)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def generar_inicial(self):
        self.status_var.set("Generando solucion con backtracking...")
        self.root.update()

        inicio = time.time()
        solucion = backtracking(self.variables, aleatorio=True)
        tiempo = time.time() - inicio

        if solucion is None:
            messagebox.showerror("Sin solucion", "No se encontro una solucion valida con las restricciones actuales.")
            self.status_var.set("No se encontro solucion valida.")
            return

        self.solucion_inicial = copy.deepcopy(solucion)
        self.solucion_actual = copy.deepcopy(solucion)

        puntaje = self.actualizar_puntaje(solucion)
        self.puntaje_inicial = puntaje
        self.actualizar_comparacion(puntaje)
        self.actualizar_validacion(solucion)
        self.mostrar_solucion(solucion)

        self.log(f"Solucion inicial generada en {tiempo:.2f}s", C["azul"])
        self.log(f"Puntaje inicial: {puntaje}/100", C["azul"])
        self.status_var.set(f"Solucion inicial generada. Puntaje: {puntaje}/100")

    def optimizar_hc(self):
        if self.solucion_actual is None:
            messagebox.showwarning("Aviso", "Primero genera una solucion inicial.")
            return

        puntaje_antes, _ = calcular_calidad(self.solucion_actual)
        self.status_var.set("Optimizando con Hill Climbing...")
        self.root.update()

        inicio = time.time()
        optimizada, historial = hill_climbing(self.solucion_actual, self.variables)
        tiempo = time.time() - inicio

        puntaje_despues = self.actualizar_puntaje(optimizada)
        self.solucion_actual = copy.deepcopy(optimizada)
        self.actualizar_comparacion(puntaje_despues)
        self.actualizar_validacion(optimizada)
        self.mostrar_solucion(optimizada)

        mejora = puntaje_despues - puntaje_antes
        signo = "+" if mejora >= 0 else ""
        self.log(f"Hill Climbing: {puntaje_antes} -> {puntaje_despues} ({signo}{mejora}) en {tiempo:.2f}s", C["verde"])
        self.log(f"Movimientos registrados: {len(historial)}", C["texto2"])
        self.status_var.set(f"Hill Climbing terminado. Puntaje: {puntaje_despues}/100")

    def optimizar_sa(self):
        if self.solucion_actual is None:
            messagebox.showwarning("Aviso", "Primero genera una solucion inicial.")
            return

        puntaje_antes, _ = calcular_calidad(self.solucion_actual)
        self.status_var.set("Optimizando con Simulated Annealing...")
        self.root.update()

        inicio = time.time()
        optimizada, historial = simulated_annealing(self.solucion_actual, self.variables)
        tiempo = time.time() - inicio

        puntaje_despues = self.actualizar_puntaje(optimizada)
        self.solucion_actual = copy.deepcopy(optimizada)
        self.actualizar_comparacion(puntaje_despues)
        self.actualizar_validacion(optimizada)
        self.mostrar_solucion(optimizada)

        mejora = puntaje_despues - puntaje_antes
        signo = "+" if mejora >= 0 else ""
        self.log(f"Simulated Annealing: {puntaje_antes} -> {puntaje_despues} ({signo}{mejora}) en {tiempo:.2f}s", C["naranja"])
        self.log(f"Iteraciones registradas: {len(historial)}", C["texto2"])
        self.status_var.set(f"Simulated Annealing terminado. Puntaje: {puntaje_despues}/100")

    def exportar_csv(self):
        if self.solucion_actual is None:
            messagebox.showwarning("Aviso", "Primero genera u optimiza un horario.")
            return

        ruta = filedialog.asksaveasfilename(
            title="Guardar horario",
            defaultextension=".csv",
            filetypes=[("Archivo CSV", "*.csv")],
            initialfile="horario_optimizado.csv",
        )
        if not ruta:
            return

        filas = []
        for (materia, sesion), (dia, hora, aula) in self.solucion_actual.items():
            filas.append({
                "Dia": dia,
                "Hora": hora,
                "Materia": materia,
                "Sesion": sesion,
                "Aula": aula,
                "Profesor": PROFESOR_MATERIA[materia],
                "Estudiantes": ESTUDIANTES_MATERIA[materia],
            })

        filas.sort(key=lambda f: (DIAS.index(f["Dia"]), HORA_INICIO[f["Hora"]], f["Materia"]))

        try:
            with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
                columnas = ["Dia", "Hora", "Materia", "Sesion", "Aula", "Profesor", "Estudiantes"]
                writer = csv.DictWriter(archivo, fieldnames=columnas)
                writer.writeheader()
                writer.writerows(filas)
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo guardar el archivo.\n{error}")
            return

        self.log(f"Horario exportado a CSV: {ruta}", C["morado"])
        self.status_var.set("Horario exportado correctamente.")

    def limpiar_resultados(self):
        # Se limpia la solucion cuando se cambian los datos.
        self.solucion_inicial = None
        self.solucion_actual = None
        self.puntaje_inicial = None
        self.construir_tabla_vacia()
        self.puntaje_label.config(text="-", fg=C["azul"])
        self.comp_label.config(text="Sin datos todavia", fg=C["texto2"])
        self.validacion_label.config(text="Restricciones duras: -", fg=C["texto2"])

        self.desglose_text.config(state="normal")
        self.desglose_text.delete("1.0", "end")
        self.desglose_text.config(state="disabled")

    def agregar_materia(self):
        dialogo = DialogoMateria(self.root, DIAS, HORARIO_BASE, MATERIAS_PROFESOR, AULAS)
        self.root.wait_window(dialogo.ventana)

        if dialogo.resultado is None:
            return

        datos = dialogo.resultado
        nombre = datos["nombre"]
        sesiones = datos["sesiones"]
        profesor = datos["profesor"]
        estudiantes = datos["estudiantes"]
        aula_pref = datos["aula"]
        restriccion = datos["restriccion"]

        # Evita materias repetidas aunque cambie mayusculas/minusculas.
        existentes = {m.lower(): m for m in SESIONES_MATERIA.keys()}
        if nombre.lower() in existentes:
            messagebox.showerror("Error", "La materia ya existe en los datos.")
            return

        if sesiones < 1 or sesiones > 3:
            messagebox.showerror("Error", "Las sesiones deben estar entre 1 y 3.")
            return

        if estudiantes > max(CAPACIDAD_AULA.values()):
            messagebox.showerror(
                "Error",
                "No existe un aula con capacidad suficiente para esa materia."
            )
            return

        # Se guarda la materia nueva en las tablas del problema.
        SESIONES_MATERIA[nombre] = sesiones
        ESTUDIANTES_MATERIA[nombre] = estudiantes
        MATERIAS_PROFESOR.setdefault(profesor, [])
        if nombre not in MATERIAS_PROFESOR[profesor]:
            MATERIAS_PROFESOR[profesor].append(nombre)
        PROFESOR_MATERIA[nombre] = profesor
        AULAS_PREFERIDAS[nombre] = [aula_pref]
        RESTRICCIONES_PROFESOR.setdefault(profesor, set())
        asignar_color_materia(nombre)

        if restriccion is not None:
            dia, hora = restriccion
            RESTRICCIONES_PROFESOR[profesor].add((dia, hora))
            texto_restriccion = f". Restriccion del profesor: {dia} {hora}"
        else:
            texto_restriccion = ""

        self.variables = generar_variables()
        self.refrescar_restricciones()
        self.limpiar_resultados()

        self.log(
            f"Materia agregada: {nombre} ({sesiones} sesion/es), profesor {profesor}, {estudiantes} estudiantes{texto_restriccion}",
            C["amarillo"],
        )

        respuesta = messagebox.askyesno(
            "Recalcular",
            f"Se agrego la materia: {nombre}.\n\n¿Quieres generar un nuevo horario con esta materia?",
        )
        if respuesta:
            self.generar_inicial()
        else:
            self.status_var.set("Materia agregada. Genera una nueva solucion para actualizar el horario.")

    def agregar_restriccion(self):
        dialogo = DialogoRestriccion(self.root, DIAS, HORARIO_BASE, MATERIAS_PROFESOR, AULAS)
        self.root.wait_window(dialogo.ventana)

        if dialogo.resultado is None:
            return

        tipo, valor, dia, hora = dialogo.resultado

        if tipo == "profesor":
            if (dia, hora) in RESTRICCIONES_PROFESOR.get(valor, set()):
                messagebox.showinfo("Aviso", f"{valor} ya tiene esa restriccion.")
                return

            RESTRICCIONES_PROFESOR.setdefault(valor, set()).add((dia, hora))
            mensaje = f"{valor} no disponible {dia} {hora}"

        else:
            if (valor, dia, hora) in AULAS_NO_DISPONIBLES:
                messagebox.showinfo("Aviso", f"{valor} ya esta ocupada en ese horario.")
                return

            AULAS_NO_DISPONIBLES.add((valor, dia, hora))
            mensaje = f"{valor} ocupada {dia} {hora}"

        self.refrescar_restricciones()
        self.log(f"Restriccion agregada: {mensaje}", C["rojo"])

        respuesta = messagebox.askyesno(
            "Recalcular",
            f"Se agrego la restriccion: {mensaje}.\n\n¿Quieres generar el horario otra vez?",
        )
        if respuesta:
            self.generar_inicial()

    def reiniciar(self):
        self.solucion_inicial = None
        self.solucion_actual = None
        self.puntaje_inicial = None

        self.construir_tabla_vacia()
        self.puntaje_label.config(text="-", fg=C["azul"])
        self.comp_label.config(text="Sin datos todavia", fg=C["texto2"])
        self.validacion_label.config(text="Restricciones duras: -", fg=C["texto2"])

        self.desglose_text.config(state="normal")
        self.desglose_text.delete("1.0", "end")
        self.desglose_text.config(state="disabled")

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

        self.status_var.set("Reiniciado. Listo para generar una nueva solucion.")

# Ventana emergente utilizada
# para agregar nuevas materias
# dinámicamente al sistema.
class DialogoMateria:
    def __init__(self, parent, dias, horario, materias_profesor, aulas):
        self.resultado = None
        self.horario = horario

        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Agregar materia")
        self.ventana.geometry("430x560")
        self.ventana.configure(bg=C["fondo"])
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.ventana.resizable(False, False)

        tk.Label(
            self.ventana,
            text="Nueva materia",
            font=("Consolas", 11, "bold"),
            bg=C["fondo"],
            fg=C["texto"],
        ).pack(pady=(18, 10))

        tk.Label(self.ventana, text="Nombre de la materia:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.nombre_var = tk.StringVar()
        tk.Entry(
            self.ventana,
            textvariable=self.nombre_var,
            width=34,
            bg=C["panel"],
            fg=C["texto"],
            insertbackground=C["texto"],
            relief="flat",
            font=("Consolas", 10),
        ).pack(padx=40, pady=(2, 10))

        tk.Label(self.ventana, text="Sesiones por semana:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.sesiones_var = tk.IntVar(value=2)
        ttk.Combobox(
            self.ventana,
            textvariable=self.sesiones_var,
            values=[1, 2, 3],
            state="readonly",
            width=32,
        ).pack(padx=40, pady=(2, 10))

        tk.Label(self.ventana, text="Profesor:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        profesores = list(materias_profesor.keys())
        self.profesor_var = tk.StringVar(value=profesores[0] if profesores else "")
        self.combo_profesor = ttk.Combobox(
            self.ventana,
            textvariable=self.profesor_var,
            values=profesores,
            width=32,
        )
        self.combo_profesor.pack(padx=40, pady=(2, 4))

        tk.Label(
            self.ventana,
            text="Puedes escoger uno existente o escribir uno nuevo",
            bg=C["fondo"],
            fg=C["texto2"],
            font=("Consolas", 8),
        ).pack(anchor="w", padx=40, pady=(0, 8))

        tk.Label(self.ventana, text="Estudiantes:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.estudiantes_var = tk.IntVar(value=20)
        tk.Spinbox(
            self.ventana,
            from_=1,
            to=max(CAPACIDAD_AULA.values()),
            textvariable=self.estudiantes_var,
            width=32,
            bg=C["panel"],
            fg=C["texto"],
            insertbackground=C["texto"],
            relief="flat",
            font=("Consolas", 10),
        ).pack(padx=40, pady=(2, 10))

        tk.Label(self.ventana, text="Aula preferida:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.aula_var = tk.StringVar(value=aulas[0])
        ttk.Combobox(
            self.ventana,
            textvariable=self.aula_var,
            values=aulas,
            state="readonly",
            width=32,
        ).pack(padx=40, pady=(2, 12))

        self.restriccion_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.ventana,
            text="Agregar horario NO disponible para este profesor",
            variable=self.restriccion_var,
            command=self.actualizar_estado_restriccion,
            bg=C["fondo"],
            fg=C["amarillo"],
            selectcolor=C["panel"],
            activebackground=C["fondo"],
            activeforeground=C["amarillo"],
            font=("Consolas", 8, "bold"),
        ).pack(anchor="w", padx=36, pady=(4, 6))

        tk.Label(self.ventana, text="Dia:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.dia_var = tk.StringVar(value=dias[0])
        self.combo_dia = ttk.Combobox(
            self.ventana,
            textvariable=self.dia_var,
            values=dias,
            state="readonly",
            width=32,
        )
        self.combo_dia.pack(padx=40, pady=(2, 10))
        self.combo_dia.bind("<<ComboboxSelected>>", self.actualizar_horas)

        tk.Label(self.ventana, text="Hora:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.hora_var = tk.StringVar()
        self.combo_hora = ttk.Combobox(
            self.ventana,
            textvariable=self.hora_var,
            values=horario[dias[0]],
            state="readonly",
            width=32,
        )
        self.combo_hora.pack(padx=40, pady=(2, 16))
        if horario[dias[0]]:
            self.combo_hora.current(0)

        tk.Button(
            self.ventana,
            text="Agregar materia",
            command=self.confirmar,
            bg=C["amarillo"],
            fg=C["oscuro"],
            font=("Consolas", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
        ).pack()

        self.actualizar_estado_restriccion()

    def actualizar_estado_restriccion(self):
        estado = "readonly" if self.restriccion_var.get() else "disabled"
        self.combo_dia.config(state=estado)
        self.combo_hora.config(state=estado)

    def actualizar_horas(self, _event=None):
        dia = self.dia_var.get()
        horas = self.horario.get(dia, [])
        self.combo_hora["values"] = horas
        if horas:
            self.combo_hora.current(0)

    def confirmar(self):
        nombre = self.nombre_var.get().strip()
        profesor = self.profesor_var.get().strip()

        if not nombre:
            messagebox.showerror("Error", "Ingresa el nombre de la materia.")
            return
        if not profesor:
            messagebox.showerror("Error", "Ingresa el nombre del profesor.")
            return

        try:
            estudiantes = int(self.estudiantes_var.get())
        except (TypeError, ValueError):
            messagebox.showerror("Error", "El numero de estudiantes no es valido.")
            return

        if estudiantes <= 0:
            messagebox.showerror("Error", "El numero de estudiantes debe ser mayor a 0.")
            return

        restriccion = None
        if self.restriccion_var.get():
            restriccion = (self.dia_var.get(), self.hora_var.get())

        self.resultado = {
            "nombre": nombre,
            "sesiones": int(self.sesiones_var.get()),
            "profesor": profesor,
            "estudiantes": estudiantes,
            "aula": self.aula_var.get(),
            "restriccion": restriccion,
        }
        self.ventana.destroy()

# Ventana emergente utilizada
# para agregar restricciones nuevas
# al problema CSP.
class DialogoRestriccion:
    def __init__(self, parent, dias, horario, materias_profesor, aulas):
        self.resultado = None
        self.horario = horario
        self.materias_profesor = materias_profesor
        self.aulas = aulas

        self.ventana = tk.Toplevel(parent)
        self.ventana.title("Agregar restriccion")
        self.ventana.geometry("400x335")
        self.ventana.configure(bg=C["fondo"])
        self.ventana.transient(parent)
        self.ventana.grab_set()
        self.ventana.resizable(False, False)

        tk.Label(
            self.ventana,
            text="Nueva restriccion",
            font=("Consolas", 11, "bold"),
            bg=C["fondo"],
            fg=C["texto"],
        ).pack(pady=(18, 10))

        tk.Label(self.ventana, text="Tipo:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.tipo_var = tk.StringVar(value="Profesor no disponible")
        self.combo_tipo = ttk.Combobox(
            self.ventana,
            textvariable=self.tipo_var,
            values=["Profesor no disponible", "Aula ocupada"],
            state="readonly",
            width=32,
        )
        self.combo_tipo.pack(padx=40, pady=(2, 10))
        self.combo_tipo.bind("<<ComboboxSelected>>", self.actualizar_valores)

        self.valor_label = tk.Label(
            self.ventana,
            text="Profesor:",
            bg=C["fondo"],
            fg=C["texto2"],
            font=("Consolas", 9),
        )
        self.valor_label.pack(anchor="w", padx=40)

        self.valor_var = tk.StringVar(value=list(materias_profesor.keys())[0])
        self.combo_valor = ttk.Combobox(
            self.ventana,
            textvariable=self.valor_var,
            values=list(materias_profesor.keys()),
            state="readonly",
            width=32,
        )
        self.combo_valor.pack(padx=40, pady=(2, 10))

        tk.Label(self.ventana, text="Dia:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.dia_var = tk.StringVar(value=dias[0])
        combo_dia = ttk.Combobox(self.ventana, textvariable=self.dia_var, values=dias, state="readonly", width=32)
        combo_dia.pack(padx=40, pady=(2, 10))
        combo_dia.bind("<<ComboboxSelected>>", self.actualizar_horas)

        tk.Label(self.ventana, text="Hora:", bg=C["fondo"], fg=C["texto2"], font=("Consolas", 9)).pack(anchor="w", padx=40)
        self.hora_var = tk.StringVar()
        self.combo_hora = ttk.Combobox(
            self.ventana,
            textvariable=self.hora_var,
            values=horario[dias[0]],
            state="readonly",
            width=32,
        )
        self.combo_hora.pack(padx=40, pady=(2, 16))
        if horario[dias[0]]:
            self.combo_hora.current(0)

        tk.Button(
            self.ventana,
            text="Agregar",
            command=self.confirmar,
            bg=C["rojo"],
            fg=C["oscuro"],
            font=("Consolas", 10, "bold"),
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
        ).pack()

    def actualizar_valores(self, _event=None):
        if self.tipo_var.get() == "Profesor no disponible":
            valores = list(self.materias_profesor.keys())
            self.valor_label.config(text="Profesor:")
        else:
            valores = self.aulas
            self.valor_label.config(text="Aula:")

        self.combo_valor["values"] = valores
        self.valor_var.set(valores[0])

    def actualizar_horas(self, _event=None):
        dia = self.dia_var.get()
        horas = self.horario.get(dia, [])
        self.combo_hora["values"] = horas
        if horas:
            self.combo_hora.current(0)

    def confirmar(self):
        tipo = "profesor" if self.tipo_var.get() == "Profesor no disponible" else "aula"
        self.resultado = (tipo, self.valor_var.get(), self.dia_var.get(), self.hora_var.get())
        self.ventana.destroy()

# Punto de entrada principal del programa.
# Inicializa la interfaz gráfica.
if __name__ == "__main__":
    random.seed()
    root = tk.Tk()
    app = OptimizerApp(root)
    root.mainloop()
