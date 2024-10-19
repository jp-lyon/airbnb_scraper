import math
import urllib.parse
import os
import json
import time
from tqdm import tqdm
from geopy.distance import geodesic

# Clear the console (adjusted for both Unix and Windows systems)
os.system("cls" if os.name == 'nt' else 'clear')

# Función para convertir diferencias de latitud y longitud a metros

def lat_lon_to_meters(lat_diff, lon_diff, avg_latitude):
    # Un grado de latitud equivale a 111,320 metros
    lat_meters = lat_diff * 111320
    # Un grado de longitud depende de la latitud (ajustado por coseno)
    lon_meters = lon_diff * 111320 * math.cos(math.radians(avg_latitude))
    return lat_meters, lon_meters

# Función para ajustar el tamaño del tile en función del nivel de zoom
def adjust_tile_size_by_zoom(tile_size, zoom_level, base_zoom=22):
    """
    Ajusta el tamaño del tile proporcionalmente al nivel de zoom.
    - tile_size: Tamaño base del tile.
    - zoom_level: Nivel de zoom actual (puede ser decimal).
    - base_zoom: Nivel de zoom base (22 en este caso).
    """
    # Ajuste proporcional según el nivel de zoom
    zoom_factor = 2 ** (base_zoom - zoom_level)  # Cuanto más bajo el zoom, mayor el área
    return tile_size * zoom_factor

def generate_airbnb_urls(
    south_lat, north_lat, west_lng, east_lng,
    tile_size_lat, tile_size_lng,
    zoom_levels
):
    all_urls_by_zoom = {}

    for zoom_level in zoom_levels:
        urls = []

        # Ajusta el tamaño del tile para latitud y longitud según el nivel de zoom
        tile_size_lat_zoomed = adjust_tile_size_by_zoom(tile_size_lat, zoom_level)
        tile_size_lng_zoomed = adjust_tile_size_by_zoom(tile_size_lng, zoom_level)

        lat_steps = int(math.ceil((north_lat - south_lat) / tile_size_lat_zoomed))
        lng_steps = int(math.ceil((east_lng - west_lng) / tile_size_lng_zoomed))
        
        total_tiles = lat_steps * lng_steps  # Número total de tiles a procesar
        start_time = time.time()  # Hora de inicio

        # Barra de progreso con tqdm
        with tqdm(total=total_tiles, desc=f'Processing Zoom Level {zoom_level}', unit='tile') as pbar:
            for i in range(lat_steps):
                for j in range(lng_steps):
                    sw_lat = south_lat + i * tile_size_lat_zoomed
                    sw_lng = west_lng + j * tile_size_lng_zoomed
                    ne_lat = min(sw_lat + tile_size_lat_zoomed, north_lat)
                    ne_lng = min(sw_lng + tile_size_lng_zoomed, east_lng)

                    # Calcular el tamaño del tile en metros
                    avg_latitude = (sw_lat + ne_lat) / 2  # Promedio de latitudes para ajustar longitud
                    lat_meters, lon_meters = lat_lon_to_meters(ne_lat - sw_lat, ne_lng - sw_lng, avg_latitude)
                    area_m2 = lat_meters * lon_meters

                    # Construye la URL de Airbnb con los parámetros ajustados
                    params = {
                        'tab_id': 'home_tab',
                        'refinement_paths[]': '/homes',
                        'channel': 'EXPLORE',
                        'query': 'Bogotá, Bogotá, D.C.',
                        'place_id': 'ChIJKcumLf2bP44RFDmjIFVjnSM',
                        'source': 'structured_search_input_header',
                        'search_type': 'user_map_move',
                        'search_mode': 'regular_search',
                        'ne_lat': ne_lat,
                        'ne_lng': ne_lng,
                        'sw_lat': sw_lat,
                        'sw_lng': sw_lng,
                        'zoom': zoom_level,  # Mantiene el nivel de zoom
                        'zoom_level': zoom_level,
                        'search_by_map': 'true'
                    }

                    # Codifica los parámetros
                    encoded_params = urllib.parse.urlencode(params, doseq=True, safe=',')
                    base_url = "https://www.airbnb.com.co/s/Bogotá--Bogotá--D.C.--Colombia/homes?"
                    url = base_url + encoded_params

                    # Añade la URL generada a la lista junto con el área en metros cuadrados
                    urls.append({
                        'zoom_level': zoom_level,
                        'sw_lat': sw_lat,
                        'sw_lng': sw_lng,
                        'ne_lat': ne_lat,
                        'ne_lng': ne_lng,
                        'tile_area_m2': area_m2,  # Tamaño del área del tile en metros cuadrados
                        'url': url
                    })

                    # Actualiza la barra de progreso
                    pbar.update(1)

                    # Calcular ETA (Tiempo Estimado de Finalización)
                    elapsed_time = time.time() - start_time
                    tiles_completed = i * lng_steps + j + 1
                    if tiles_completed > 0:
                        eta = elapsed_time / tiles_completed * (total_tiles - tiles_completed)
                        pbar.set_postfix(ETA=f'{eta:.2f}s')

        # Almacena las URLs por nivel de zoom
        all_urls_by_zoom[zoom_level] = urls

    return all_urls_by_zoom

# Define los límites de Bogotá
south_latitude = 4.555   # Límite sur
north_latitude = 4.835   # Límite norte
west_longitude = -74.150  # Límite oeste
east_longitude = -74.028  # Límite este

# Define el tamaño base del tile (esto cambiará en función del zoom)
tile_size_latitude = 0.0002  # Aproximadamente 550 metros de latitud
tile_size_longitude = 0.0002  # Aproximadamente 550 metros de longitud

# Define los niveles de zoom que quieres probar
zoom_levels = [14, 16, 18, 20, 22]  # Niveles de zoom a probar

# Genera las URLs
urls_by_zoom = generate_airbnb_urls(
    south_latitude, north_latitude, west_longitude, east_longitude,
    tile_size_latitude, tile_size_longitude,
    zoom_levels
)

# Escribir las URLs en archivos JSON separados por nivel de zoom
for zoom_level, urls in urls_by_zoom.items():
    # Nombre del archivo JSON con el nivel de zoom
    json_file = f'/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_{zoom_level}.json'
    
    # Guardar cada entrada de URL como una línea JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        for entry in urls:
            # Guardar cada entrada de URL correctamente formateada
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')  # Escribir cada URL en una línea separada
    
    # Mensaje de confirmación por cada archivo creado
    print(f"{len(urls)} URLs for zoom level {zoom_level} have been saved to '{json_file}'.")
