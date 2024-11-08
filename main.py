import os
import json
import time
import random
import logging
import psutil
import requests
import re
import signal
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

# Clase AirbnbScraper con el método extract_lat_lon
class AirbnbScraper:
    def extract_lat_lon(self, idPublication):
        attempts = 0
        success = False

        while not success and attempts < 10:
            try:
                URL = 'https://www.airbnb.com.co/rooms/'
                r = requests.get(URL + str(idPublication))
                p_lat = re.compile(r'"lat":([-0-9.]+),')
                p_lon = re.compile(r'"lng":([-0-9.]+),')
                lat_matches = p_lat.findall(r.text)
                lon_matches = p_lon.findall(r.text)
                if lat_matches and lon_matches:
                    lat = lat_matches[0]
                    lon = lon_matches[0]
                    success = True
                    return float(lat), float(lon)
                else:
                    raise ValueError("No se encontraron coordenadas.")
            except Exception as e:
                logging.warning(f'No hay coordenada, intento número: {attempts + 1}')
                logging.warning(f'Error: {e}')
                attempts += 1
                time.sleep(1)  # Esperar un segundo antes de reintentar
        return 0.0, 0.0

def extract_last_comment_date(idPublication: str) -> str:
    try:
        URL = f'https://www.airbnb.com.co/rooms/{idPublication}/reviews'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        r = requests.get(URL, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')

        dates_comments = soup.find_all('div', class_='s78n3tv')

        if dates_comments:
            last_comment = dates_comments[-1].get_text(strip=True)
            print(f"Último comentario encontrado: {last_comment}")
            return last_comment
        else:
            print(f"No se encontraron comentarios para la publicación {idPublication}")
            return ""

    except Exception as e:
        print(f"Error al extraer la fecha del último comentario para la publicación {idPublication}: {e}")
        return ""

# Función para monitorear y loguear el uso de memoria
def log_memory_usage():
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 ** 2)  # Convertir a MB
    logging.info(f"Uso de memoria: {mem:.2f} MB")

# Función para esperar un tiempo específico
def wait_for_page_load(seconds):
    time.sleep(seconds)

# Función que clasifica si es habitación o apartamento
def roomOrHouse(TypeDescription: str) -> str:
    """
    Clasifica descripciones si es habitación o apartamento
    """
    if TypeDescription.startswith("Habitación"):
        return "room"
    else:
        return "house"

# Función para extraer datos de las tarjetas en la página actual
def extract_listings(driver, sw_lat, sw_lng, ne_lat, ne_lng, zoom_level):
    cards_data = []
    try:
        # Wait for the cards to be present
        wait = WebDriverWait(driver, 10)
        cards = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "cy5jw6o")))
        cards = cards[:100]  # Limit to first 100 elements
        logging.info(f"Encontrados {len(cards)} elementos para procesar.")

        # Instantiate the AirbnbScraper class
        scraper = AirbnbScraper()

        for index, card in enumerate(cards):
            try:
                # Extract data from the card
                try:
                    link_component = card.find_element(By.CLASS_NAME, "bn2bl2p").get_attribute("href")
                    listing_id = link_component.split("/")[-1].split("?")[0]  # Extract ID from URL
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

                # Get coordinates using the extract_lat_lon method
                try:
                    lat, lon = scraper.extract_lat_lon(listing_id)
                except Exception:
                    lat, lon = 0.0, 0.0

                # Do not extract last_comment_date here
                last_comment = None

                # Add data to the list
                data = {
                    "id": listing_id,
                    "link": link_component,
                    "location": location,
                    "description": description,
                    "image": image,
                    "price": price,
                    "rating": rating,
                    "latitude": lat,
                    "longitude": lon,
                    "last_comment_date": last_comment,  # Will extract later
                    "sw_lat": sw_lat,
                    "sw_lng": sw_lng,
                    "ne_lat": ne_lat,
                    "ne_lng": ne_lng,
                    "zoom_level": zoom_level,
                    "TypeRoomOrHouse": roomOrHouse(description) if description else "unknown"
                }
                cards_data.append(data)

            except StaleElementReferenceException:
                logging.warning(f"StaleElementReferenceException encountered at index {index}. Skipping this card.")
                continue
            except Exception as e:
                logging.error(f"Error processing card at index {index}: {e}")
                continue

    except Exception as e:
        logging.error(f"Error al extraer listados: {e}")

    return cards_data

# Cargar datos JSON desde un archivo
def load_json_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as json_file:
            try:
                data = json.load(json_file)
                if not data:
                    logging.info(f"El archivo {filepath} está vacío.")
                    return {}
                return data
            except json.JSONDecodeError as e:
                logging.error(f"Error al cargar JSON desde {filepath}: {e}")
                return {}
    else:
        logging.info(f"El archivo {filepath} no existe.")
        return {}

# Guardar datos JSON en un archivo
def save_json_data(filepath, data):
    with open(filepath, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

# Funciones para el checkpoint
def load_checkpoint(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as json_file:
            try:
                data = json.load(json_file)
                return data.get("last_url", "")
            except json.JSONDecodeError as e:
                logging.error(f"Error al cargar JSON desde {filepath}: {e}")
                return ""
    else:
        return ""

def save_checkpoint(filepath, url):
    data = {"last_url": url}
    with open(filepath, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file)

# Variable global para indicar si el usuario ha solicitado detener el programa
stop_requested = False

# Función para manejar la señal de interrupción (Ctrl+C)
def signal_handler(sig, frame):
    global stop_requested
    stop_requested = True
    logging.info("Interrupción del usuario detectada. Guardando estado y deteniendo el programa...")

# Función para extraer enlaces siguientes y manejarlos eficientemente
def extract_data_in_groups(driver, json_files):
    global stop_requested

    # Directorio del archivo maestro
    master_filepath = "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_master_listings.json"
    master_dir = os.path.dirname(master_filepath)

    # Cargar datos existentes del master
    master_data = load_json_data(master_filepath)
    logging.info(f"El archivo maestro contiene actualmente {len(master_data)} listados.")

    # Convertir master_data a DataFrame
    if master_data:
        master_df = pd.DataFrame.from_dict(master_data, orient='index')
        master_df.reset_index(inplace=True)
    else:
        master_df = pd.DataFrame()

    logging.info(f"El archivo maestro contiene actualmente {len(master_df)} listados.")

    # Checkpoint mechanism
    checkpoint_filepath = os.path.join(master_dir, "checkpoint.json")
    last_processed_url = load_checkpoint(checkpoint_filepath)
    checkpoint_found = last_processed_url == ""  # If no checkpoint URL, start processing immediately

    # Procesar archivos JSON directamente
    for idx, json_file in enumerate(tqdm(json_files, desc="Procesando archivos JSON", unit="archivo")):
        logging.info(f"Procesando archivo JSON: {json_file}")

        # Load the data from the JSON file into a DataFrame
        try:
            with open(json_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                data_list = [json.loads(line.strip()) for line in lines]
                df_links = pd.DataFrame(data_list)
        except Exception as e:
            logging.error(f"Error al cargar datos del archivo {json_file}: {e}")
            continue

        if not checkpoint_found:
            if last_processed_url in df_links['url'].values:
                checkpoint_found = True
                logging.info(f"Checkpoint URL found in file {json_file}. Resuming from there.")
                # Filter the DataFrame to start from the checkpoint
                idx_checkpoint = df_links.index[df_links['url'] == last_processed_url].tolist()[0]
                df_links = df_links.iloc[idx_checkpoint+1:]
            else:
                logging.info(f"Checkpoint URL not found in file {json_file}. Skipping this file.")
                continue  # Skip this file

        # Process each URL in the DataFrame
        for idx_row, row in df_links.iterrows():
            if stop_requested:
                break
            try:
                url_json = row['url']
                sw_lat = row['sw_lat']
                sw_lng = row['sw_lng']
                ne_lat = row['ne_lat']
                ne_lng = row['ne_lng']
                zoom_level = row['zoom_level']

                logging.info(f"Procesando link: {url_json} con coordenadas: {sw_lat}, {sw_lng}, {ne_lat}, {ne_lng}")

                # Verificar si el driver está activo
                if driver.session_id is None:
                    logging.warning("El driver ha perdido la sesión. Re-iniciando el driver...")
                    driver.quit()
                    driver = setup_webdriver()

                try:
                    driver.get(url_json)
                    wait_for_page_load(3)
                    log_memory_usage()

                    # Extrae listados de la página actual
                    cards_data = extract_listings(driver, sw_lat, sw_lng, ne_lat, ne_lng, zoom_level)

                    if cards_data:
                        logging.info(f"Se encontraron {len(cards_data)} nuevos listados.")

                        # Extract last_comment_date for each listing
                        for card_data in cards_data:
                            listing_id = card_data['id']
                            if listing_id != "unknown":
                                try:
                                    last_comment = extract_last_comment_date(listing_id)
                                    card_data['last_comment_date'] = last_comment
                                except Exception as e:
                                    logging.error(f"Error extracting last_comment_date for listing {listing_id}: {e}")
                                    card_data['last_comment_date'] = None

                        # Convertir cards_data a DataFrame
                        cards_df = pd.DataFrame(cards_data)

                        # Merge with master_df
                        if not master_df.empty:
                            master_df = pd.concat([master_df, cards_df], ignore_index=True)
                        else:
                            master_df = cards_df

                        # Eliminar duplicados basados en 'id'
                        master_df.drop_duplicates(subset='id', keep='last', inplace=True)

                        # Guardar el JSON maestro actualizado
                        master_df.set_index('id', inplace=True)
                        master_df.to_json(master_filepath, orient='index', indent=4, force_ascii=False)
                        master_df.reset_index(inplace=True)  # Reset index for future concatenations
                        logging.info(f"Datos extraídos y agregados al archivo maestro: {master_filepath}")
                        logging.info(f"El archivo maestro contiene actualmente {len(master_df)} listados.")
                    else:
                        logging.info("No se encontraron nuevos listados en esta página.")

                    # Save the checkpoint
                    save_checkpoint(checkpoint_filepath, url_json)

                except WebDriverException as e:
                    logging.error(f"Error del WebDriver al procesar el enlace {url_json}: {e}")
                    driver.quit()
                    driver = setup_webdriver()
                    continue
                except Exception as e:
                    logging.error(f"Error al procesar el enlace {url_json}: {e}")
                    continue

            except Exception as e:
                logging.error(f"Error al procesar la fila {idx_row} del archivo {json_file}: {e}")
                continue

        if stop_requested:
            break

    logging.info("Todos los archivos JSON han sido procesados.")

    logging.info(f"El archivo maestro contiene actualmente {len(master_df)} listados.")

    return master_df  # Retorna los datos maestros actualizados

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

# Agregar la función get_zoom_level
def get_zoom_level(filename):
    match = re.search(r'zoom_(\d+)', filename)
    return int(match.group(1)) if match else 0

def main():
    global stop_requested

    # Registrar el manejador de señal para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Lista de archivos JSON con niveles de zoom (rutas completas)
    json_files = [
        "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_14.json",
        "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_16.json",
        "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_18.json",
        "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_20.json",
    ]

    # Ordenar por nivel de zoom
    json_files = sorted(json_files, key=get_zoom_level)

    # Imprimir el orden de los archivos para verificar
    print("Procesando archivos en el siguiente orden:")
    for f in json_files:
        print(f)

    driver = setup_webdriver()
    try:
        master_df = extract_data_in_groups(driver, json_files)
    except Exception as e:
        logging.error(f"Error en el proceso principal: {e}")
    finally:
        driver.quit()
        logging.info("WebDriver cerrado correctamente.")

        # Guardar estado final si el programa fue detenido
        if stop_requested:
            logging.info("Estado final guardado después de la interrupción.")

if __name__ == "__main__":
    main()
