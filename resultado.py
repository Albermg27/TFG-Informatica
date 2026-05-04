import folium
import requests

def obtener_ruta_real(puntos):
    coords = ";".join(f"{lon},{lat}" for lat, lon in puntos)
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"

    try:
        r = requests.get(url)
        data = r.json()
        geometry = data["routes"][0]["geometry"]["coordinates"]
        return [(lat, lon) for lon, lat in geometry]
    except:
        print("Error obteniendo ruta real")
        return puntos

def visualizar_rutas(cuadrillas, visitas_no_asignadas):
    mapa = folium.Map(location=[40.42, -3.70], zoom_start=12)

    colores = ["red", "blue", "green", "purple", "orange"]

    for idx, c in enumerate(cuadrillas):
        color = colores[idx % len(colores)]
        almacen = (40.5409, -3.6420)
        puntos_ruta = [almacen]

        for visita, t_ini, t_fin in c.historial:
            lat, lon = visita.latitud, visita.longitud
            puntos_ruta.append((lat, lon))

            folium.Marker(
                location=(lat, lon),
                popup=f"""
                <b>{visita.nombre}</b><br>
                Cuadrilla: {c.id}<br>
                Inicio: {t_ini} min<br>
                Fin: {t_fin} min<br>
                Duración: {t_fin - t_ini} min
                """,
                icon=folium.Icon(color=color)
            ).add_to(mapa)

        if len(puntos_ruta) > 1:
            ruta_real = obtener_ruta_real(puntos_ruta)

            folium.PolyLine(
                ruta_real,
                color=color,
                weight=4,
                opacity=0.8
            ).add_to(mapa)

    for v in visitas_no_asignadas:
        folium.Marker(
            location=(v.latitud, v.longitud),
            popup=f"""
            <b>{v.nombre}</b><br>
            NO ASIGNADA
            """,
            icon=folium.Icon(color="gray", icon="info-sign")
        ).add_to(mapa)

    mapa.save("mapa.html")
    print("\nMapa generado: mapa.html")