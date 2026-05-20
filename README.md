# Proyecto IA – Optimizador de Horarios

## Integrantes
* Melissa Guerra
* Stiven Viscaino
* Jorge Yanez

## Descripción

Este proyecto consiste en un sistema de generación y optimización de horarios académicos utilizando técnicas de Inteligencia Artificial.

El problema es modelado como un CSP (*Constraint Satisfaction Problem*) y posteriormente optimizado mediante algoritmos de búsqueda local.

El sistema permite:

* Generar horarios académicos automáticamente.
* Validar restricciones duras.
* Evaluar restricciones blandas.
* Optimizar la calidad del horario.
* Visualizar horarios mediante una interfaz gráfica.
* Exportar resultados en formato CSV.

---

# Objetivo del Proyecto

Desarrollar un sistema inteligente capaz de construir horarios académicos válidos y optimizados para estudiantes y profesores, evitando conflictos de tiempo y mejorando la distribución de clases.

---

# Técnicas de Inteligencia Artificial Utilizadas

## CSP (Constraint Satisfaction Problem)

El problema se modela mediante:

* Variables
* Dominios
* Restricciones

Cada variable representa una sesión de una materia.

Ejemplo:

```python
("Programacion", 1)
```

El dominio de cada variable contiene todas las combinaciones posibles de:

* Día
* Hora
* Aula

---

## Algoritmos Implementados

### 1. Backtracking

Algoritmo principal utilizado para construir soluciones válidas.

Características:

* Asignación incremental.
* Verificación de restricciones.
* Retroceso automático ante conflictos.

---

### 2. MRV (Minimum Remaining Values)

Heurística utilizada en el CSP.

Selecciona primero la variable con menor cantidad de valores disponibles para reducir el espacio de búsqueda.

---

### 3. Hill Climbing

Algoritmo de búsqueda local que mejora una solución inicial realizando pequeños cambios.

Objetivo:

* Reducir penalizaciones.
* Mejorar la calidad del horario.

---

### 4. Random Restart

Estrategia utilizada junto a Hill Climbing.

Consiste en:

* Reiniciar el algoritmo varias veces.
* Evitar óptimos locales.

---

### 5. Simulated Annealing

Algoritmo de optimización inspirado en el enfriamiento de metales.

Permite aceptar temporalmente soluciones peores para escapar de óptimos locales.

---

# Restricciones del Sistema

## Restricciones Duras

Las restricciones duras deben cumplirse obligatoriamente.

* Un estudiante no puede tener dos clases al mismo tiempo.
* Un profesor no puede dictar dos materias simultáneamente.
* Un aula no puede ser utilizada por dos clases al mismo tiempo.
* Una materia no puede repetirse el mismo día.
* Se respetan horarios no disponibles de profesores.
* Se valida capacidad del aula.
* Se evita invadir el horario de almuerzo.

---

## Restricciones Blandas

Las restricciones blandas generan penalizaciones en la función objetivo.

* Evitar clases muy temprano.
* Evitar clases tarde el viernes.
* Preferencia de aulas para ciertas materias.
* Reducir huecos en el horario.
* Mejor distribución semanal.

---

# Estructura del Proyecto

```text
Proyecto/
│
├── main.py
└── README.md
```

---

# Datos Utilizados

## Materias

* Programacion
* Fisica
* Matematicas
* Redes
* Base de Datos

---

## Profesores

| Profesor | Materias            |
| -------- | ------------------- |
| Juan     | Programacion, Redes |
| Ana      | Matematicas         |
| Carlos   | Fisica              |
| Luis     | Base de Datos       |

---

## Aulas

| Aula  | Capacidad |
| ----- | --------- |
| Aula1 | 20        |
| Aula2 | 30        |
| Lab1  | 25        |
| Lab2  | 20        |

---

# Función Objetivo

La calidad del horario se evalúa mediante una función de puntuación.

La solución inicia con una puntuación base y se aplican:

* Penalizaciones.
* Bonificaciones.

Mientras menor sea la penalización, mejor será el horario generado.

## Pesos utilizados

| Restricción blanda           | Peso |
|-----------------------------|------|
| Clases a las 7AM            | -3 pts |
| Viernes en la tarde         | -5 pts |
| Aula no preferida           | -2 pts |
| Huecos en el horario        | -3 pts |
| Mala distribución semanal   | -3 pts |

Estos pesos permiten que los algoritmos de búsqueda local prioricen horarios más cómodos y equilibrados para los estudiantes.

---

# Interfaz Gráfica

El sistema utiliza Tkinter para construir una interfaz gráfica.

Características:

* Generación automática de horarios.
* Visualización organizada.
* Comparación entre algoritmos.
* Exportación CSV.
* Gestión de restricciones.

---

# Requisitos

## Python

Se recomienda utilizar:

```text
Python 3.10 o superior
```

---

# Librerías Utilizadas

```python
tkinter
random
copy
math
time
csv
typing
```

---

# Instalación

## 1. Clonar el repositorio

```bash
git clone https://github.com/jorgelys2310-alt/Pryecto_1B_IA.git
```

---

## 2. Ingresar al proyecto

```bash
cd Proyecto
```

---

## 3. Ejecutar el sistema

```bash
python main.py
```

---

# Ejemplo de Funcionamiento

1. El sistema genera todas las variables del CSP.
2. Se construyen dominios válidos.
3. Backtracking genera una solución inicial.
4. Hill Climbing o Simulated Annealing optimizan el horario.
5. El resultado se muestra en pantalla.

---

# Resultados Esperados

El sistema debe:

* Generar horarios válidos.
* Minimizar conflictos.
* Optimizar distribución semanal.
* Reducir huecos.
* Mejorar calidad general del horario.
