import math
import urllib.parse
import os
import json
import time
import random
import gc
import logging
import psutil
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
from tqdm import tqdm  # Importar tqdm para la barra de progreso

from bs4 import BeautifulSoup
import requests


# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)



def extract_first_comment(driver, listing_id):
    """
    Extrae la fecha del primer comentario para un listado dado.

    Args:
        driver: Instancia de Selenium WebDriver
        listing_id: ID de listado de Airbnb

    Returns:
        str: Fecha del primer comentario, o None si no se encuentran comentarios
    """
    try:
        review_url = f'https://www.airbnb.com.co/rooms/{listing_id}/reviews'
        logging.info(f"Accediendo a las reseñas para el listado {listing_id}: {review_url}")
        
        # Navegar a la página de reseñas
        driver.get(review_url)
        
        # Esperar a que se carguen los comentarios usando WebDriverWait
        try:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
        
            dates_comments = soup.find_all('div', class_='s78n3tv')
            if dates_comments:
                last_comment = dates_comments[-1].get_text(strip=True)
                return last_comment
            else:
                logging.warning(f"Texto de fecha de comentario vacío encontrado para el listado {listing_id}")
                return None
                
        except TimeoutException:
            logging.info(f"No se encontraron comentarios dentro del período de espera para el listado {listing_id}")
            return None
        except NoSuchElementException:
            logging.info(f"No se encontraron comentarios para el listado {listing_id}")
            return None
            
    except Exception as e:
        logging.error(f"Error al extraer el primer comentario para el listado {listing_id}: {e}", exc_info=True)
        return None



# Función para monitorear y loguear el uso de memoria
def log_memory_usage():
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 ** 2)  # Convertir a MB
    logging.info(f"Uso de memoria: {mem:.2f} MB")

# Función para esperar un tiempo específico
def wait_for_page_load(seconds):
    time.sleep(seconds)

# Funcion que clasifica si es habitacion o apto
def roomOrHouse(TypeDescription:str)->str:
    """
    clasifica descripciones si es habitacion o apto
    """
    if TypeDescription.startswith("Habitación"):
        return "room"
    else: return "house"


# Función para extraer datos de las tarjetas en la página actual
def extract_listings(driver, sw_lat, sw_lng, ne_lat, ne_lng, zoom_level):
    cards_data = []
    try:
        # Limitar el número de elementos procesados
        cards = driver.find_elements(By.CLASS_NAME, "cy5jw6o")[:100]  # Procesar solo los primeros 100 elementos
        logging.info(f"Encontrados {len(cards)} elementos para procesar.")

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
                price = card.find_element(By.CLASS_NAME, "_11jcbg2").text
            except NoSuchElementException:
                price = "No price"

            try:
                rating = card.find_element(By.CLASS_NAME, "r4a59j5").text
            except NoSuchElementException:
                rating = "No rating"

            # Extraer primer comentario     
            first_comment = None
            if listing_id != "unknown":
                first_comment = extract_first_comment(driver, listing_id)


            # Añadir coordenadas, nivel de zoom e ID extraídos de la URL
            data = {
                "id": listing_id,
                "link": link_component,
                "location": location,
                "description": description,
                "image": image,
                "price": price,
                "rating": rating,
                "first_comment_date": first_comment,
                "sw_lat": sw_lat,
                "sw_lng": sw_lng,
                "ne_lat": ne_lat,
                "ne_lng": ne_lng,
                "zoom_level": zoom_level,  # Incluir el nivel de zoom
                "TypeRoomOrHouse": roomOrHouse(description) if description else "unknown"
            }

            cards_data.append(data)

    except Exception as e:
        logging.error(f"Error al extraer listados: {e}")

    return cards_data

# Cargar datos JSON desde un archivo
def load_json_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as json_file:
            try:
                return json.load(json_file)
            except json.JSONDecodeError as e:
                logging.error(f"Error al cargar JSON desde {filepath}: {e}")
                return {}
    return {}

# Guardar datos JSON en un archivo
def save_json_data(filepath, data):
    with open(filepath, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# Función para extraer enlaces siguientes y manejarlos eficientemente
def extract_data_in_groups(driver, json_files):
    master_filepath = "./airbnb_master_listings.json"
    master_data = load_json_data(master_filepath)
    logging.info(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

    df_visited_links = pd.DataFrame(columns=['link', 'visited', 'sw_lat', 'sw_lng', 'ne_lat', 'ne_lng', 'zoom_level'])
    df_pending_links = pd.DataFrame(columns=['link', 'visited', 'sw_lat', 'sw_lng', 'ne_lat', 'ne_lng', 'zoom_level'])

    # Barra de progreso para los archivos JSON
    for json_file in tqdm(json_files, desc="Procesando archivos JSON", unit="archivo"):
        logging.info(f"Procesando archivo JSON: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            random.shuffle(lines)  # Mezclar líneas para evitar patrones
            
            # Barra de progreso para las líneas dentro del archivo JSON
            for line in tqdm(lines, desc=f"Procesando {os.path.basename(json_file)}", unit="línea", leave=False):
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
                    new_entry = {
                        'link': url_json,
                        'visited': False,
                        'sw_lat': sw_lat,
                        'sw_lng': sw_lng,
                        'ne_lat': ne_lat,
                        'ne_lng': ne_lng,
                        'zoom_level': zoom_level
                    }
                    df_pending_links = pd.concat([pd.DataFrame([new_entry]), df_pending_links], ignore_index=True)

                except json.JSONDecodeError as e:
                    logging.error(f"Error al decodificar JSON en {json_file}: {e}")
                    continue

    # Procesa los enlaces pendientes con una barra de progreso
    pending_total = len(df_pending_links)
    with tqdm(total=pending_total, desc="Procesando enlaces pendientes", unit="enlace") as pbar:
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
                pbar.update(1)
                continue

            logging.info(f"Procesando link: {current_link} con coordenadas: {sw_lat}, {sw_lng}, {ne_lat}, {ne_lng}")

            try:
                # Abre el enlace
                driver.get(current_link)
                wait_for_page_load(3)
                log_memory_usage()

                # Extrae listados de la página actual
                cards_data = extract_listings(driver, sw_lat, sw_lng, ne_lat, ne_lng, zoom_level)

                if cards_data:
                    logging.info(f"Se encontraron {len(cards_data)} nuevos listados.")
                    for card in cards_data:
                        listing_id = card["id"]
                        if listing_id in master_data:
                            # Si el ID ya existe, comparar los niveles de zoom
                            if int(card["zoom_level"]) > int(master_data[listing_id]["zoom_level"]):
                                master_data[listing_id] = card  # Actualizar si el nuevo nivel de zoom es mayor
                                logging.info(f"Actualizando el listado con ID {listing_id} a un nivel de zoom mayor: {zoom_level}")
                        else:
                            # Si el ID no existe, agregarlo
                            master_data[listing_id] = card
                            logging.info(f"Agregando nuevo listado con ID {listing_id}")

                    # Guardar el JSON maestro actualizado
                    save_json_data(master_filepath, master_data)
                    logging.info(f"Datos extraídos y agregados al archivo maestro: {master_filepath}")
                    logging.info(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

                    # Eliminar duplicados en el archivo maestro
                    master_data_unique = {v['id']: v for v in master_data.values()}
                    duplicates_removed = len(master_data) - len(master_data_unique)
                    master_data = master_data_unique
                    save_json_data(master_filepath, master_data)
                    logging.info(f"Se eliminaron {duplicates_removed} listados duplicados. El archivo maestro contiene ahora {len(master_data)} listados.")
                else:
                    logging.info("No se encontraron nuevos listados en esta página.")

                # Extrae nuevos enlaces de la página actual
                try:
                    wait = WebDriverWait(driver, 5)
                    buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "c1ackr0h")))
                    for button in buttons:
                        link = button.get_attribute("href")
                        if link and (not df_visited_links['link'].eq(link).any()) and (not df_pending_links['link'].eq(link).any()):
                            new_entry = {
                                'link': link,
                                'visited': False,
                                'sw_lat': sw_lat,
                                'sw_lng': sw_lng,
                                'ne_lat': ne_lat,
                                'ne_lng': ne_lng,
                                'zoom_level': zoom_level
                            }
                            df_pending_links = pd.concat([pd.DataFrame([new_entry]), df_pending_links], ignore_index=True)
                            logging.info(f"Encontrado nuevo enlace: {link}")
                except TimeoutException:
                    logging.warning("No se encontraron nuevos botones de enlace en la página actual.")

                # Marcar el enlace actual como visitado y mover al DataFrame de visitados
                df_pending_links.loc[df_pending_links['link'] == current_link, 'visited'] = True
                new_visited = {
                    'link': current_link,
                    'visited': True,
                    'sw_lat': sw_lat,
                    'sw_lng': sw_lng,
                    'ne_lat': ne_lat,
                    'ne_lng': ne_lng,
                    'zoom_level': zoom_level
                }
                df_visited_links = pd.concat([pd.DataFrame([new_visited]), df_visited_links], ignore_index=True)
                log_memory_usage()

                # Recolección de basura para liberar memoria
                gc.collect()
                log_memory_usage()

                # Actualizar la barra de progreso
                pbar.update(1)

            except Exception as e:
                logging.error(f"Error al procesar el enlace {current_link}: {e}")
                # Marcar como visitado para evitar bloqueos
                df_pending_links.loc[df_pending_links['link'] == current_link, 'visited'] = True
                df_visited_links = pd.concat([pd.DataFrame([{
                    'link': current_link,
                    'visited': True,
                    'sw_lat': sw_lat,
                    'sw_lng': sw_lng,
                    'ne_lat': ne_lat,
                    'ne_lng': ne_lng,
                    'zoom_level': zoom_level
                }]), df_visited_links], ignore_index=True)
                gc.collect()
                pbar.update(1)
                continue

    logging.info("Todos los enlaces de las páginas han sido visitados.")
    master_data = load_json_data(master_filepath)
    logging.info(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

# Configuración del WebDriver en modo headless y optimizado
def setup_webdriver():
    options = Options()
    options.headless = True  # Ejecutar en modo headless (sin mostrar la ventana)

    # Deshabilitar imágenes para reducir el consumo de memoria
    profile = webdriver.FirefoxProfile()
    profile.set_preference("permissions.default.image", 2)
    profile.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", "false")
    options.profile = profile

    # Añadir preferencias adicionales para optimizar el rendimiento
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)

    # Iniciar el WebDriver
    driver = webdriver.Firefox(options=options)
    return driver

def main():
    # Limpiar la consola
    os.system("clear")

    # Lista de archivos JSON con niveles de zoom (rutas completas)
    json_files = [
        "./airbnb_urls_bogota_zoom_14.json",
        "./airbnb_urls_bogota_zoom_16.json",
        "./airbnb_urls_bogota_zoom_18.json",
        "./airbnb_urls_bogota_zoom_20.json",
    ]

    # Configurar y utilizar el WebDriver dentro de un context manager
    driver = setup_webdriver()
    try:
        # Extraer datos de los archivos JSON
        extract_data_in_groups(driver, json_files)
    except Exception as e:
        logging.error(f"Error en el proceso principal: {e}")
    finally:
        # Asegurar que el WebDriver se cierre correctamente
        driver.quit()
        logging.info("WebDriver cerrado correctamente.")

if __name__ == "__main__":
    main()
