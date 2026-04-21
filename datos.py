from modelos import Visita, Cuadrilla, Material, EstadoCuadrilla, TipoVisita

import requests

def crear_matriz_distancias(visitas):
    coords = ";".join(f"{v.longitud},{v.latitud}" for v in visitas)
    url = f"http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration"
    
    D = {}
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        durations = data['durations']
        for i, row in enumerate(durations):
            D[i] = {}
            for j, dur in enumerate(row):
                D[i][j] = round(dur / 60, 1)
    except:
        print("Error al obtener la matriz de OSRM")
        for i in range(len(visitas)):
            D[i] = {j: float('inf') for j in range(len(visitas))}
    return D

def actualizar_matriz_distancias(D, visitas, nueva_visita):
    nuevo_idx = len(visitas) - 1

    D[nuevo_idx] = {}

    for i, v in enumerate(visitas):
        if v is nueva_visita:
            continue

        coords = f"{nueva_visita.longitud},{nueva_visita.latitud};{v.longitud},{v.latitud}"
        url = f"http://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration"

        try:
            r = requests.get(url)
            data = r.json()
            dur = data["durations"][0][1] / 60

            D[nuevo_idx][i] = round(dur, 1)
            D[i][nuevo_idx] = round(dur, 1)

        except:
            D[nuevo_idx][i] = float("inf")
            D[i][nuevo_idx] = float("inf")

    return D

def cargar_datos():

    # Materiales M y N_m
    materiales = {
        1: Material(1, 35),
        2: Material(2, 18),
        3: Material(3, 12),
        4: Material(4, 20),
        5: Material(5, 15),
        6: Material(6, 25),
        7: Material(7, 10),
        8: Material(8, 14)
    }

    # Visitas (V0)
    V0 = []

    visitas_data = [
        (None, 0, {}, "Almacén", 40.5409, -3.6420),

        (TipoVisita.INSTALACION, 10, {1:6, 2:2, 4:1, 6:2}, "Cliente A", 40.4179, -3.7102),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente B", 40.4225, -3.7128),
        (TipoVisita.INCIDENCIA, 9, {2:2, 3:1, 6:1}, "Cliente C", 40.4261, -3.7055),
        (TipoVisita.INSTALACION, 8, {1:5, 4:1, 5:1}, "Cliente D", 40.4302, -3.6998),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente E", 40.4339, -3.7067),
        (TipoVisita.INCIDENCIA, 10, {2:3, 3:1, 6:2}, "Cliente F", 40.4380, -3.7132),
        (TipoVisita.INSTALACION, 7, {1:4, 3:1, 5:1, 8:1}, "Cliente G", 40.4415, -3.7180),
        (TipoVisita.TECNICA, 3, {6:1}, "Cliente H", 40.4448, -3.7109),
        (TipoVisita.INCIDENCIA, 6, {3:2, 6:1}, "Cliente I", 40.4482, -3.7035),
        (TipoVisita.INSTALACION, 9, {1:7, 4:1, 7:1}, "Cliente J", 40.4520, -3.6978),
        (TipoVisita.TECNICA, 6, {6:1}, "Cliente K", 40.4561, -3.7089),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente L", 40.4590, -3.7155),
        (TipoVisita.INSTALACION, 9, {1:5, 5:2, 8:1}, "Cliente M", 40.4625, -3.7012),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente N", 40.4658, -3.6945),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente O", 40.4692, -3.7060),
        (TipoVisita.INSTALACION, 10, {1:6, 2:2, 7:1}, "Cliente P", 40.4720, -3.7130),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente Q", 40.4745, -3.7200),
        (TipoVisita.INCIDENCIA, 6, {2:3, 3:1}, "Cliente R", 40.4770, -3.7085),
        (TipoVisita.INSTALACION, 8, {1:5, 4:1, 8:1}, "Cliente S", 40.4795, -3.6990),
        (TipoVisita.TECNICA, 3, {6:1}, "Cliente T", 40.4820, -3.7110),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente U", 40.5450, -3.6350),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente V", 40.5475, -3.6600),
        (TipoVisita.INSTALACION, 9, {1:7, 5:2}, "Cliente W", 40.5500, -3.6355),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente X", 40.5525, -3.6650),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente Y", 40.5550, -3.6325),
        (TipoVisita.INSTALACION, 10, {1:6, 2:2, 7:1}, "Cliente Z", 40.5575, -3.6675),
        (TipoVisita.INSTALACION, 10, {1:8, 4:2, 5:1, 7:1}, "Cliente AA", 40.5970, -3.7070),
        (TipoVisita.TECNICA, 5, {}, "Cliente AB", 40.6020, -3.7130),
        (TipoVisita.INCIDENCIA, 9, {2: 1}, "Cliente AC", 40.5160, -3.6070),
        (TipoVisita.INSTALACION, 8, {1: 2}, "Cliente AD", 40.5205, -3.6120),
        (TipoVisita.TECNICA, 6, {}, "Cliente AE", 40.4910, -3.5800),
        (TipoVisita.INCIDENCIA, 7, {3: 1}, "Cliente AF", 40.4950, -3.5750),
        (TipoVisita.INSTALACION, 9, {1:7, 5:2, 8:1}, "Cliente AG", 40.5030, -3.5320),
        (TipoVisita.TECNICA, 4, {}, "Cliente AH", 40.5080, -3.5380),
        (TipoVisita.INSTALACION, 8, {1: 2}, "Cliente AI", 40.4740, -3.6540),
        (TipoVisita.TECNICA, 5, {}, "Cliente AJ", 40.4780, -3.6480),
        (TipoVisita.INCIDENCIA, 6, {2: 1}, "Cliente AK", 40.4710, -3.6600),
        (TipoVisita.INSTALACION, 10, {1:9, 2:3, 7:1}, "Cliente AL", 40.3230, -3.8670),
        (TipoVisita.TECNICA, 5, {}, "Cliente AM", 40.3280, -3.8600),
        (TipoVisita.INCIDENCIA, 7, {3: 1}, "Cliente AN", 40.2440, -3.6960),
        (TipoVisita.TECNICA, 4, {}, "Cliente AO", 40.2480, -3.7020),
        (TipoVisita.INSTALACION, 9, {1:6, 4:1, 5:1}, "Cliente AP", 40.4350, -3.8130),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente AQ", 40.4385, -3.8060),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente AR", 40.4420, -3.7990),
        (TipoVisita.INSTALACION, 10, {1:7, 2:2, 7:1}, "Cliente AS", 40.4475, -3.7920),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente AT", 40.5460, -3.6380),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente AU", 40.5490, -3.6310),
        (TipoVisita.INSTALACION, 9, {1:6, 5:2}, "Cliente AV", 40.5520, -3.6240),
        (TipoVisita.INSTALACION, 10, {1:8, 4:2, 8:1}, "Cliente AW", 40.5550, -3.6170),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente AX", 40.3080, -3.7320),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente AY", 40.3040, -3.7260),
        (TipoVisita.INSTALACION, 9, {1:6, 4:1, 5:1}, "Cliente AZ", 40.3000, -3.7200),
        (TipoVisita.INSTALACION, 10, {1:7, 2:2, 7:1}, "Cliente BA", 40.2960, -3.7140),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente BB", 40.3440, -3.8240),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente BC", 40.3480, -3.8180),
        (TipoVisita.INSTALACION, 9, {1:6, 5:2}, "Cliente BD", 40.3520, -3.8120),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente BE", 40.3980, -3.6130),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente BF", 40.3940, -3.6070),
        (TipoVisita.INSTALACION, 9, {1:6, 4:1, 8:1}, "Cliente BG", 40.3900, -3.6010),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente BH", 40.5080, -3.8780),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente BI", 40.5120, -3.8720),
        (TipoVisita.INSTALACION, 10, {1:8, 2:2, 7:1}, "Cliente BJ", 40.5160, -3.8660),
        (TipoVisita.TECNICA, 4, {6:1}, "Cliente BK", 40.4050, -3.8820),
        (TipoVisita.INCIDENCIA, 8, {2:2, 3:1}, "Cliente BL", 40.4090, -3.8760),
        (TipoVisita.INSTALACION, 9, {1:6, 5:2}, "Cliente BM", 40.4130, -3.8700),
        (TipoVisita.TECNICA, 5, {6:1}, "Cliente BN", 40.4680, -3.5840),
        (TipoVisita.INCIDENCIA, 7, {3:2, 6:1}, "Cliente BO", 40.4640, -3.5780),
        (TipoVisita.INSTALACION, 10, {1:7, 2:2, 8:1}, "Cliente BP", 40.4600, -3.5720),
        (TipoVisita.INSTALACION, 10, {1:9, 4:2, 7:1}, "Cliente BQ", 40.5250, -3.9000),
        (TipoVisita.INSTALACION, 10, {1:9, 2:3, 8:1}, "Cliente BR", 40.2850, -3.7600),
    ]

    for tipo, prioridad, materiales_req, nombre, lat, lon in visitas_data:
        v = Visita(tipo=tipo, prioridad=prioridad, nombre=nombre, latitud=lat, longitud=lon)
        v.materiales_necesarios = materiales_req
        V0.append(v)

    # Cuadrillas (C)
    C = []

    for i in range(1, 4):
        c = Cuadrilla(i, EstadoCuadrilla.LIBRE)
        c.posicion = 0
        c.tiempo_acumulado = 0
        C.append(c)

    # PARÁMETROS
    params = {
        "alpha": 1,
        "beta": 0,
        "gamma": 1000,
        "J": 1000,
        "M_big": 1000,
    }

    # DISTANCIAS
    D = crear_matriz_distancias(V0)

    V0.pop(0)

    return V0, C, materiales, params, D