import math
import urllib.parse
import os
import json
import time
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.firefox.options import Options  # Importar las opciones para Firefox
import pandas as pd
from urllib.parse import urlparse, parse_qs

# Function to wait for a specific amount of time
def wait_for_page_load(seconds):
    time.sleep(seconds)
    

# Function to extract the data from the cards on the current page
def extract_listings(sw_lat, sw_lng, ne_lat, ne_lng, zoom_level):
    cards_data = []
    cards = driver.find_elements(By.CLASS_NAME, "cy5jw6o")
    for card in cards:
        try:
            link_component = card.find_element(By.CLASS_NAME, "bn2bl2p").get_attribute("href")
            listing_id = link_component.split("/")[-1].split("?")[0]  # Extraer el ID desde la URL
        except NoSuchElementException:
            link_component = "No link"
            listing_id = "unknown"

        try:
            location = card.find_element(By.CLASS_NAME, "t1jojoys").text
        except NoSuchElementException:
            location = "No location"

        try:
            description = card.find_element(By.CLASS_NAME, "s1cjsi4j").text
        except NoSuchElementException:
            description = "No description"

        try:
            image = card.find_element(By.CLASS_NAME, "itu7ddv").get_attribute("src")
        except NoSuchElementException:
            image = "No image"

        try:
            price = card.find_element(By.CLASS_NAME, "pquyp1l").text
        except NoSuchElementException:
            price = "No price"

        try:
            rating = card.find_element(By.CLASS_NAME, "r4a59j5").text
        except NoSuchElementException:
            rating = "No rating"

        # Añadir coordenadas, nivel de zoom e ID extraídos de la URL
        data = {
            "id": listing_id,
            "link": link_component,
            "location": location,
            "description": description,
            "image": image,
            "price": price,
            "rating": rating,
            "sw_lat": sw_lat,
            "sw_lng": sw_lng,
            "ne_lat": ne_lat,
            "ne_lng": ne_lng,
            "zoom_level": zoom_level  # Incluir el nivel de zoom
        }

        cards_data.append(data)

    return cards_data

# Cargar datos JSON desde un archivo
def load_json_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as json_file:
            return json.load(json_file)
    return {}

# Guardar datos JSON en un archivo
def save_json_data(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# Function to extract links for the next set of pages from the current page
def extract_next_links():
    try:
        wait = WebDriverWait(driver, 3)  # Reducir el tiempo de espera a 3 segundos
        buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "c1ackr0h")))
        links = [button.get_attribute("href") for button in buttons if button.get_attribute("href")]
        return links
    except TimeoutException:
        # Si no encuentra el elemento, devolver una lista vacía y continuar
        print(f"No se encontró el elemento en 3 segundos, continuando...")
        return []
    except Exception as e:
        print(f"Error al extraer los enlaces: {e}")
        return []

# Function to save results every 100 extractions
def save_partial_results(extracted_coordinates, total_extractions):
    partial_file = f'/home/jjleo/Entorno/Python/airbnb_scraper/extracted_results_partial_{total_extractions}.json'
    with open(partial_file, 'w', encoding='utf-8') as f:
        for coords in extracted_coordinates:
            json.dump(coords, f, ensure_ascii=False, indent=4)  # Formato legible
            f.write('\n')  # Guardar cada línea en una nueva línea
    print(f'{total_extractions} extracciones guardadas en {partial_file}.')

# Function to extract data in groups of pages and estimate ETA
def extract_data_in_groups(starting_links, group_size=3, max_pages=15):
    master_df = pd.DataFrame()
    links_to_process = starting_links
    page_count = 0
    start_time = time.time()
    extracted_coordinates = []  # Lista para almacenar las coordenadas extraídas
    total_extractions = 0  # Contador para controlar las extracciones
    failed_attempts = 0  # Contador de intentos fallidos consecutivos

    # Cargar el archivo maestro si ya existe
    master_data = load_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")

    # Total expected pages to process
    total_pages = max_pages

    while links_to_process and page_count <= max_pages:
        for i, link in enumerate(links_to_process[:group_size]):
            driver.execute_script(f"window.open('{link}', '_blank');")
        wait_for_page_load(5)

        for j in range(len(driver.window_handles) - 1, 0, -1):
            driver.switch_to.window(driver.window_handles[j])
            wait_for_page_load(2)

            # Extraer coordenadas de la URL abierta
            url = driver.current_url
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            sw_lat = query_params.get('sw_lat', ['unknown'])[0]
            sw_lng = query_params.get('sw_lng', ['unknown'])[0]
            ne_lat = query_params.get('ne_lat', ['unknown'])[0]
            ne_lng = query_params.get('ne_lng', ['unknown'])[0]
            zoom_level = query_params.get('zoom_level', ['unknown'])[0]

            # Extraer los listados con las coordenadas, el nivel de zoom y el ID
            cards_data = extract_listings(sw_lat, sw_lng, ne_lat, ne_lng, zoom_level)
            print(f"Datos extraídos de la pestaña {j}: {len(cards_data)} cards")

            if cards_data:
                failed_attempts = 0  # Reiniciar el contador si se encuentran listados
                df_current = pd.DataFrame(cards_data)
                master_df = pd.concat([master_df, df_current], ignore_index=True)

                # Guardar coordenadas de las URLs de éxito
                extracted_coordinates.append({
                    'sw_lat': sw_lat,
                    'sw_lng': sw_lng,
                    'ne_lat': ne_lat,
                    'ne_lng': ne_lng
                })

                # Actualizar el maestro revisando niveles de zoom
                for card in cards_data:
                    listing_id = card["id"]
                    if listing_id in master_data:
                        # Si el ID ya existe, comparar los niveles de zoom
                        if int(card["zoom_level"]) > int(master_data[listing_id]["zoom_level"]):
                            master_data[listing_id] = card  # Actualizar si el nuevo nivel de zoom es mayor
                    else:
                        # Si el ID no existe, agregarlo
                        master_data[listing_id] = card

                # Actualizar contador de extracciones
                total_extractions += 1

                # Guardar cada 100 extracciones
                if total_extractions % 100 == 0:
                    save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
                    extracted_coordinates.clear()  # Limpia la lista para la siguiente ronda
            else:
                failed_attempts += 1
                print(f"No se encontraron listados. Intento fallido #{failed_attempts}")
                if failed_attempts >= 25:
                    print(f"Se omitió la zona después de {failed_attempts} intentos fallidos consecutivos.")
                    return master_df  # Salir de esta zona

            if j == 1:
                new_links = extract_next_links()
                links_to_process = new_links

            driver.close()
            page_count += 1
            if page_count >= max_pages:
                break

        driver.switch_to.window(driver.window_handles[0])

    # Guardar el JSON maestro al final del proceso
    save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)

    return master_df

# Function to process JSON files

def process_json_files(json_files):
    total_pages = 0
    pages_processed = 0
    start_time = time.time()

    # Precalcular el número de páginas que se espera procesar basado en los archivos JSON
    for json_file in json_files:
        with open(json_file, 'r') as file:
            # Leer línea por línea cada objeto JSON en lugar de cargar todo el archivo a la vez
            for line in file:
                try:
                    data = json.loads(line.strip())  # Procesar cada línea como un objeto JSON
                    total_pages += 15  # O ajusta según la lógica que prefieras
                except json.JSONDecodeError as e:
                    print(f"Error al decodificar JSON en {json_file}: {e}")
                    continue

    for json_file in json_files:
        with open(json_file, 'r') as file:
            for line in file:
                try:
                    data = json.loads(line.strip())  # Procesar cada línea como un objeto JSON
                    zoom_level = data['zoom_level']
                    sw_lat = data['sw_lat']
                    sw_lng = data['sw_lng']
                    ne_lat = data['ne_lat']
                    ne_lng = data['ne_lng']
                    url = data['url']

                    print(f"Procesando zoom_level: {zoom_level} con coordenadas: {sw_lat}, {sw_lng}, {ne_lat}, {ne_lng}")
                    
                    # Abrir el navegador con la URL correspondiente
                    driver.get(url)
                    wait_for_page_load(3)  # Esperar a que cargue la página

                    # Manejo de StaleElementReferenceException
                    retries = 3
                    while retries > 0:
                        try:
                            # Verificar si hay más de 15 resultados
                            element = WebDriverWait(driver, 3).until(  # Espera de 3 segundos
                                EC.presence_of_element_located((By.CLASS_NAME, "c1ackr0h"))
                            )
                            if int(element.text) <= 15:
                                print(f"Menos de 15 resultados encontrados en el zoom level {zoom_level}. Extrayendo datos...")
                                extract_and_save_data(url)
                                break
                            else:
                                print(f"Más de 15 resultados encontrados en el zoom level {zoom_level}. Pasando al siguiente nivel de zoom...")
                            
                            # Actualizar las páginas procesadas
                            pages_processed += 1
                            break
                        except TimeoutException:
                            print(f"No se encontró el elemento después de 3 segundos en el zoom level {zoom_level}. Continuando...")
                            break
                        except StaleElementReferenceException:
                            retries -= 1
                            print(f"Elemento no disponible en el DOM. Reintentando ({retries} intentos restantes)...")
                    
                except json.JSONDecodeError as e:
                    print(f"Error al decodificar JSON en {json_file}: {e}")
                    continue

# Function to extract data and save to a single master JSON
def extract_and_save_data(url):
    # Extraer las coordenadas de la URL
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    sw_lat = query_params.get('sw_lat', ['unknown'])[0]
    sw_lng = query_params.get('sw_lng', ['unknown'])[0]
    ne_lat = query_params.get('ne_lat', ['unknown'])[0]
    ne_lng = query_params.get('ne_lng', ['unknown'])[0]
    zoom_level = query_params.get('zoom_level', ['unknown'])[0]

    driver.get(url)
    wait_for_page_load(3)  # Esperar a que la página se cargue completamente
    cards_data = extract_listings(sw_lat, sw_lng, ne_lat, ne_lng, zoom_level)

    # Cargar el archivo maestro si ya existe
    master_data = load_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")

    if cards_data:
        # Actualizar el maestro revisando niveles de zoom
        for card in cards_data:
            listing_id = card["id"]
            if listing_id in master_data:
                # Si el ID ya existe, comparar los niveles de zoom
                if int(card["zoom_level"]) > int(master_data[listing_id]["zoom_level"]):
                    master_data[listing_id] = card  # Actualizar si el nuevo nivel de zoom es mayor
            else:
                # Si el ID no existe, agregarlo
                master_data[listing_id] = card

        # Guardar el JSON maestro actualizado
        save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
        print(f"Datos extraídos y agregados al archivo maestro: /home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")
    # Extraer las coordenadas de la URL
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    sw_lat = query_params.get('sw_lat', ['unknown'])[0]
    sw_lng = query_params.get('sw_lng', ['unknown'])[0]
    ne_lat = query_params.get('ne_lat', ['unknown'])[0]
    ne_lng = query_params.get('ne_lng', ['unknown'])[0]
    zoom_level = query_params.get('zoom_level', ['unknown'])[0]

    driver.get(url)
    wait_for_page_load(3)  # Esperar a que la página se cargue completamente
    cards_data = extract_listings(sw_lat, sw_lng, ne_lat, ne_lng, zoom_level)

    # Cargar el archivo maestro si ya existe
    master_data = load_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")

    if cards_data:
        # Actualizar el maestro revisando niveles de zoom
        for card in cards_data:
            listing_id = card["id"]
            if listing_id in master_data:
                # Si el ID ya existe, comparar los niveles de zoom
                if int(card["zoom_level"]) > int(master_data[listing_id]["zoom_level"]):
                    master_data[listing_id] = card  # Actualizar si el nuevo nivel de zoom es mayor
            else:
                # Si el ID no existe, agregarlo
                master_data[listing_id] = card

        # Guardar el JSON maestro actualizado
        save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
        print(f"Datos extraídos y agregados al archivo maestro: /home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")

# Set up the WebDriver in headless mode
options = Options()
options.headless = True  # Ejecutar en modo headless (sin mostrar la ventana)

driver = webdriver.Firefox(options=options)  # Pasar las opciones al inicializar Firefox
os.system("clear")

# List of JSON files with zoom levels (full paths)
json_files = [
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_14.json",
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_16.json",
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_18.json",
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_20.json"
]

try:
    # Process the JSON files with ETA estimation
    process_json_files(json_files)

finally:
    driver.quit()
