# TFG

Aplicación de escritorio en Python para planificar y simular la asignación de visitas de cuadrillas de instalación solar en el área de Madrid. Incluye optimización con Gurobi, cálculo de rutas con OSRM y una interfaz gráfica (Tkinter).

## Requisitos previos

| Componente | Versión / notas |
|------------|-----------------|
| **Python** | 3.10 o superior |
| **Gurobi** | Solver instalado y licencia activa ([gurobi.com](https://www.gurobi.com/)) |
| **Conexión a internet** | Necesaria para consultar la API pública de OSRM al calcular matrices de distancias |
| **Tkinter** | Incluido con Python en Windows. En Linux: `sudo apt install python3-tk` |

## Instalación

1. Clona o descarga el repositorio y abre una terminal en la carpeta raíz del proyecto.

2. (Recomendado) Crea y activa un entorno virtual:

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

3. Instala las dependencias de Python:

```bash
pip install sqlalchemy requests folium gurobipy
```

4. Asegúrate de que Gurobi está correctamente instalado y que la licencia está configurada (`grbgetkey` o licencia académica).

## Carga de datos

Los escenarios de prueba se almacenan en una base de datos **SQLite** (`tfg.db` en la raíz del proyecto). Los datos no se generan en memoria: deben cargarse antes de usar la aplicación.

### Primera vez (crear base de datos y cargar todo)

Ejecuta desde la raíz del proyecto:

```bash
python -m database.init_db
```

Este comando:

1. **Elimina** las tablas existentes (si las hay).
2. **Crea** el esquema de la base de datos.
3. **Inserta** los datos iniciales mediante el script de *seed*.

Al finalizar verás mensajes como `Base de datos creada` y `SEED COMPLETADO`.

### Qué datos se cargan

El script `database/seed.py` inserta:

- **Instancia operativa (id = 0)** — Dataset completo con todas las visitas del catálogo repartidas por Madrid. Es la instancia que usa la interfaz gráfica (visitas, cuadrillas, materiales, planificación y sistema dinámico).
- **10 instancias de simulación (id = 1…10)** — Escenarios con distinto número de visitas, distribución geográfica, duración de jornada y stock de materiales. Se usan en el módulo de simulación y estadísticas.

Cada instancia incluye:

- Visitas (almacén central + clientes con coordenadas en Madrid).
- Materiales y stock de almacén.
- Tres cuadrillas con su inventario inicial.
- Requisitos de material por visita.

### Recargar datos sin borrar el esquema

Si las tablas ya existen y solo quieres **vaciar y volver a insertar** los datos:

```bash
python -m database.seed
```

### Reinicio completo

Para empezar de cero (borra `tfg.db` y la recrea):

```bash
python -m database.init_db
```

> **Nota:** Si ejecutas la aplicación sin haber cargado datos, fallará al intentar leer visitas, materiales o cuadrillas desde la base de datos vacía.

## Levantar la aplicación

Con el entorno virtual activado y los datos ya cargados:

```bash
python app_gui.py
```

Se abrirá la ventana **Planificador de Cuadrillas** (1280×760). Al arrancar, la aplicación:

1. Carga los datos de la instancia operativa desde SQLite.
2. Consulta OSRM para construir las matrices de tiempos y distancias (la **primera ejecución puede tardar varios minutos** según la conexión y el número de visitas).
3. Inicializa el sistema dinámico en memoria.
4. Muestra la pantalla de **Visitas**.

### Secciones de la interfaz

| Pantalla | Descripción |
|----------|-------------|
| Visitas | Catálogo de visitas y materiales requeridos |
| Cuadrillas | Estado de las tres cuadrillas |
| Materiales | Stock del almacén |
| Planificación | Ejecuta el plan estático y genera el mapa (`mapa.html`) |
| Dinámico | Replanificación ante eventos (nuevas visitas, cancelaciones, etc.) |
| Simulación | Simulación de jornadas con las 10 instancias de prueba |
| Estadísticas | Métricas agregadas y exportación de informes |

El mapa de rutas se guarda como `mapa.html` en la raíz del proyecto y se abre desde el navegador al planificar.

## Flujo recomendado

```
1. pip install …          → dependencias
2. python -m database.init_db   → crear BD y cargar datos
3. python app_gui.py      → lanzar la GUI
```

## Estructura del proyecto (resumen)

```
├── app_gui.py              # Punto de entrada de la aplicación
├── database/
│   ├── init_db.py          # Crear esquema + seed inicial
│   ├── seed.py             # Carga de datos en SQLite
│   ├── models.py           # Modelos SQLAlchemy
│   └── session.py          # Conexión a tfg.db
├── datos.py                # Lectura BD → objetos + matrices OSRM
├── gui/                    # Interfaz gráfica (Tkinter)
├── model.py                # Modelo de optimización (Gurobi)
├── sistema_estatico.py     # Planificación estática
├── sistema_dinamico.py     # Replanificación dinámica
├── simulacion/             # Motor de simulación y métricas
└── osrm_client.py          # Cliente HTTP para OSRM
```

## Problemas frecuentes

**`gurobipy` / licencia Gurobi**  
Verifica que Gurobi está instalado y que `python -c "import gurobipy; gurobipy.Model()"` no devuelve error de licencia.

**Error de OSRM / timeout**  
La aplicación usa el servidor público `router.project-osrm.org`. Comprueba la conexión a internet. Si el servicio está saturado, espera y vuelve a intentarlo.

**Base de datos vacía o corrupta**  
Ejecuta de nuevo `python -m database.init_db`.

**Tkinter no encontrado (Linux)**  
Instala el paquete del sistema: `sudo apt install python3-tk`.
