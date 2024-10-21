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
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, NoSuchWindowException
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
    
# Function to extract data in groups of pages
def extract_data_in_groups(json_files, group_size=3):
    master_data = load_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")
    print(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

    visited_links = set()  # Conjunto para almacenar los enlaces ya visitados

    for json_file in json_files:
        with open(json_file, 'r') as file:
            lines = file.readlines()
            random.shuffle(lines)  # Mezclar aleatoriamente las líneas del archivo JSON
            for line in lines:
                try:
                    data = json.loads(line.strip())  # Procesar cada línea como un objeto JSON
                    zoom_level = data['zoom_level']
                    sw_lat = data['sw_lat']
                    sw_lng = data['sw_lng']
                    ne_lat = data['ne_lat']
                    ne_lng = data['ne_lng']
                    url = data['url']

                    if url in visited_links:
                        print(f"El enlace {url} ya fue visitado. Saltando...")
                        continue  # Saltar si el enlace ya fue visitado

                    visited_links.add(url)  # Agregar el enlace al conjunto de visitados

                    print(f"Procesando zoom_level: {zoom_level} con coordenadas: {sw_lat}, {sw_lng}, {ne_lat}, {ne_lng}")
                    driver.get(url)
                    wait_for_page_load(3)  # Esperar a que cargue la página

                    # Extraer listados de la página actual
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
                        master_data_unique = {v['id']: v for v in master_data.values()}  # Usar el ID como clave para asegurar unicidad
                        duplicates_removed = len(master_data) - len(master_data_unique)
                        master_data = master_data_unique
                        save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
                        print(f"Se eliminaron {duplicates_removed} listados duplicados. El archivo maestro contiene ahora {len(master_data)} listados.")
                    else:
                        print("No se encontraron nuevos listados en esta página.")

                    # Extraer los enlaces siguientes y procesarlos
                    next_links = extract_next_links()
                    while next_links:
                        for link in next_links[:group_size]:
                            if link in visited_links:
                                print(f"El enlace {link} ya fue visitado. Saltando...")
                                continue  # Saltar si el enlace ya fue visitado

                            visited_links.add(link)  # Agregar el enlace al conjunto de visitados

                            # Obtener el handle de la pestaña actual (antigua)
                            old_tab = driver.current_window_handle

                            # Abrir la nueva pestaña
                            driver.execute_script(f"window.open('{link}', '_blank');")
                            wait_for_page_load(5)

                            # Obtener todos los handles de las pestañas
                            handles = driver.window_handles

                            # Identificar el handle de la nueva pestaña
                            new_tab = [h for h in handles if h != old_tab][0]

                            # Cambiar a la nueva pestaña
                            driver.switch_to.window(new_tab)
                            wait_for_page_load(2)

                            # Cerrar la pestaña antigua
                            driver.switch_to.window(old_tab)
                            driver.close()

                            # Cambiar de nuevo a la nueva pestaña
                            driver.switch_to.window(new_tab)

                            # Extraer listados de la pestaña abierta
                            try:
                                cards_data = extract_listings(sw_lat, sw_lng, ne_lat, ne_lng, zoom_level)
                            except NoSuchWindowException:
                                print("La pestaña fue cerrada inesperadamente. Continuando con la siguiente pestaña...")
                                continue

                            if cards_data:
                                print(f"Se encontraron {len(cards_data)} nuevos listados en la pestaña actual.")
                                for card in cards_data:
                                    listing_id = card["id"]
                                    if listing_id in master_data:
                                        if int(card["zoom_level"]) > int(master_data[listing_id]["zoom_level"]):
                                            master_data[listing_id] = card
                                            print(f"Actualizando el listado con ID {listing_id} a un nivel de zoom mayor: {zoom_level}")
                                    else:
                                        master_data[listing_id] = card
                                        print(f"Agregando nuevo listado con ID {listing_id}")

                                save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
                                print(f"Datos extraídos y agregados al archivo maestro: /home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")
                                print(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

                                # Eliminar duplicados en el archivo maestro
                                master_data_unique = {v['id']: v for v in master_data.values()}  # Usar el ID como clave para asegurar unicidad
                                duplicates_removed = len(master_data) - len(master_data_unique)
                                master_data = master_data_unique
                                save_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json", master_data)
                                print(f"Se eliminaron {duplicates_removed} listados duplicados. El archivo maestro contiene ahora {len(master_data)} listados.")
                            else:
                                print(f"No se encontraron nuevos listados en la pestaña actual.")

                        next_links = extract_next_links()

                except json.JSONDecodeError as e:
                    print(f"Error al decodificar JSON en {json_file}: {e}")
                    continue

    master_data = load_json_data("/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json")
    print(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

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
    # Extract data from JSON files
    extract_data_in_groups(json_files)
finally:
    driver.quit()
