import math
import urllib.parse
import os
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    NoSuchWindowException,
)
from selenium.webdriver.firefox.options import Options
import pandas as pd
from urllib.parse import urlparse, parse_qs

# Función para esperar un tiempo específico
def wait_for_page_load(seconds):
    time.sleep(seconds)

# Función para extraer datos de las tarjetas en la página actual
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
            "zoom_level": zoom_level,  # Incluir el nivel de zoom
        }

        cards_data.append(data)

    return cards_data

# Cargar datos JSON desde un archivo
def load_json_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as json_file:
            return json.load(json_file)
    return {}

# Guardar datos JSON en un archivo
def save_json_data(filepath, data):
    with open(filepath, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# Función para extraer enlaces siguientes y manejarlos eficientemente
def extract_data_in_groups(json_files):
    master_data = load_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")
    print(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

    df_visited_links = pd.DataFrame(columns=['link', 'visited', 'sw_lat', 'sw_lng', 'ne_lat', 'ne_lng', 'zoom_level'])
    df_pending_links = pd.DataFrame(columns=['link', 'visited', 'sw_lat', 'sw_lng', 'ne_lat', 'ne_lng', 'zoom_level'])

    for json_file in json_files:
        with open(json_file, 'r') as file:
            lines = file.readlines()
            random.shuffle(lines)
            for line in lines:
                try:
                    data = json.loads(line.strip())
                    url_json = data['url']
                    sw_lat = data['sw_lat']
                    sw_lng = data['sw_lng']
                    ne_lat = data['ne_lat']
                    ne_lng = data['ne_lng']
                    zoom_level = data['zoom_level']

                    # Verifica si el enlace ya ha sido visitado o está pendiente de ser visitado
                    if ((not df_visited_links.empty and (df_visited_links['link'] == url_json).any()) or
                        (not df_pending_links.empty and (df_pending_links['link'] == url_json).any())):
                        continue

                    # Inicializa los enlaces por visitar para esta página
                    df_pending_links = pd.concat([pd.DataFrame({
                        'link': [url_json],
                        'visited': [False],
                        'sw_lat': [sw_lat],
                        'sw_lng': [sw_lng],
                        'ne_lat': [ne_lat],
                        'ne_lng': [ne_lng],
                        'zoom_level': [zoom_level]
                    }), df_pending_links], ignore_index=True)

                    # Procesa los enlaces en df_pending_links
                    while not df_pending_links[df_pending_links['visited'] == False].empty:
                        current_row = df_pending_links[df_pending_links['visited'] == False].iloc[0]
                        current_link = current_row['link']
                        sw_lat = current_row['sw_lat']
                        sw_lng = current_row['sw_lng']
                        ne_lat = current_row['ne_lat']
                        ne_lng = current_row['ne_lng']
                        zoom_level = current_row['zoom_level']

                        # Verifica nuevamente si el enlace ya fue visitado
                        if (not df_visited_links.empty and (df_visited_links['link'] == current_link).any()):
                            df_pending_links.loc[df_pending_links['link'] == current_link, 'visited'] = True
                            continue

                        print(f"Procesando link: {current_link} con coordenadas: {sw_lat}, {sw_lng}, {ne_lat}, {ne_lng}")
                        # Abre el enlace
                        driver.get(current_link)
                        wait_for_page_load(3)

                        # Extrae listados de la página actual
                        cards_data = extract_listings(sw_lat, sw_lng, ne_lat, ne_lng, zoom_level)

                        if cards_data:
                            print(f"Se encontraron {len(cards_data)} nuevos listados.")
                            for card in cards_data:
                                listing_id = card["id"]
                                if listing_id in master_data:
                                    # Si el ID ya existe, comparar los niveles de zoom
                                    if int(card["zoom_level"]) > int(master_data[listing_id]["zoom_level"]):
                                        master_data[listing_id] = card  # Actualizar si el nuevo nivel de zoom es mayor
                                        print(f"Actualizando el listado con ID {listing_id} a un nivel de zoom mayor: {zoom_level}")
                                else:
                                    # Si el ID no existe, agregarlo
                                    master_data[listing_id] = card
                                    print(f"Agregando nuevo listado con ID {listing_id}")

                            # Guardar el JSON maestro actualizado
                            save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
                            print(f"Datos extraídos y agregados al archivo maestro: /home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")
                            print(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

                            # Eliminar duplicados en el archivo maestro
                            master_data_unique = {v['id']: v for v in master_data.values()}
                            duplicates_removed = len(master_data) - len(master_data_unique)
                            master_data = master_data_unique
                            save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
                            print(f"Se eliminaron {duplicates_removed} listados duplicados. El archivo maestro contiene ahora {len(master_data)} listados.")
                        else:
                            print("No se encontraron nuevos listados en esta página.")

                        # Extrae nuevos enlaces de la página actual
                        wait = WebDriverWait(driver, 5)
                        try:
                            buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "c1ackr0h")))
                            for button in buttons:
                                link = button.get_attribute("href")
                                if link and (not df_visited_links.empty and not (df_visited_links['link'] == link).any()) and not (df_pending_links['link'] == link).any():
                                    df_pending_links = pd.concat([pd.DataFrame({
                                        'link': [link],
                                        'visited': [False],
                                        'sw_lat': [sw_lat],
                                        'sw_lng': [sw_lng],
                                        'ne_lat': [ne_lat],
                                        'ne_lng': [ne_lng],
                                        'zoom_level': [zoom_level]
                                    }), df_pending_links], ignore_index=True)
                        except TimeoutException:
                            pass

                        # Marcar el enlace actual como visitado y mover al DataFrame de visitados
                        df_pending_links.loc[df_pending_links['link'] == current_link, 'visited'] = True
                        df_visited_links = pd.concat([pd.DataFrame({
                            'link': [current_link],
                            'visited': [True],
                            'sw_lat': [sw_lat],
                            'sw_lng': [sw_lng],
                            'ne_lat': [ne_lat],
                            'ne_lng': [ne_lng],
                            'zoom_level': [zoom_level]
                        }), df_visited_links], ignore_index=True)

                except json.JSONDecodeError as e:
                    print(f"Error al decodificar JSON en {json_file}: {e}")
                    continue

    print("Todos los enlaces de las páginas han sido visitados.")
    master_data = load_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")
    print(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

# Configuración del WebDriver en modo headless
options = Options()
options.headless = True  # Ejecutar en modo headless (sin mostrar la ventana)

driver = webdriver.Firefox(options=options)  # Pasar las opciones al inicializar Firefox
os.system("clear")

# Lista de archivos JSON con niveles de zoom (rutas completas)
json_files = [
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_14.json",
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_16.json",
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_18.json",
    "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_20.json",
]

try:
    # Extraer datos de los archivos JSON
    extract_data_in_groups(json_files)
finally:
    driver.quit()
