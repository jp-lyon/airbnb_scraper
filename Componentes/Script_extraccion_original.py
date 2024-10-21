from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd
import os
import time
import json
from tqdm import tqdm

# Function to wait for a specific amount of time
def wait_for_page_load(seconds):
    time.sleep(seconds)

# Function to extract the data from the cards on the current page
def extract_listings():
    cards_data = []
    cards = driver.find_elements(By.CLASS_NAME, "cy5jw6o")
    for card in cards:
        try:
            # Intentar extraer cada elemento y manejar excepciones si no se encuentra
            try:
                link_component = card.find_element(By.CLASS_NAME, "bn2bl2p").get_attribute("href")
            except NoSuchElementException:
                link_component = "No link"

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

            data = {
                "link": link_component,
                "location": location,
                "description": description,
                "image": image,
                "price": price,
                "rating": rating
            }

            cards_data.append(data)

        except (NoSuchElementException, TimeoutException) as e:
            print(f"Error al extraer un card: {e}")
            continue
    return cards_data

# Function to extract links for the next set of pages from the current page
def extract_next_links():
    try:
        wait = WebDriverWait(driver, 10)
        buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "c1ackr0h")))
        links = [button.get_attribute("href") for button in buttons if button.get_attribute("href")]
        return links
    except Exception as e:
        print(f"Error al extraer los enlaces: {e}")
        return []

def extract_data_in_groups(starting_links, group_size=3, max_pages=15):
    # DataFrame acumulador grande
    master_df = pd.DataFrame()

    # Inicializar con los primeros enlaces
    links_to_process = starting_links
    page_count = 0

    # Crear barra de progreso
    with tqdm(total=max_pages, desc="Progreso de extracción", unit="página", ncols=100, ascii=True) as pbar:
        while links_to_process and page_count < max_pages:
            # Abrir el grupo de pestañas en una iteración
            for i, link in enumerate(links_to_process[:group_size]):
                driver.execute_script(f"window.open('{link}', '_blank');")

            # Esperar solo una vez después de abrir el último enlace usando la función wait_for_page_load
            wait_for_page_load(5)  # Esperar 5 segundos después de abrir el último enlace

            # Procesar las pestañas abiertas y extraer datos de la última
            for j in range(len(driver.window_handles) - 1, 0, -1):
                driver.switch_to.window(driver.window_handles[j])

                # Esperar 2 segundos adicionales antes de extraer datos
                wait_for_page_load(2)

                # Extraer los datos de la pestaña actual
                cards_data = extract_listings()

                # Actualizar la barra de progreso y añadir un salto de línea
                pbar.update(1)
                print("\n")  # Añadir salto de línea

                print(f"Datos extraídos de la pestaña {j}: {len(cards_data)} cards")
                print('\n')

                if cards_data:
                    df_current = pd.DataFrame(cards_data)
                    master_df = pd.concat([master_df, df_current], ignore_index=True)

                # Al llegar a la última pestaña del grupo, buscar nuevos enlaces para el siguiente grupo
                if j == 1:
                    new_links = extract_next_links()

                    # Agregar los nuevos enlaces a procesar en la siguiente iteración
                    links_to_process = new_links

                # Cerrar la pestaña actual
                driver.close()

                # Incrementar el contador de páginas procesadas
                page_count += 1
                if page_count >= max_pages:
                    break

            # Volver a la pestaña principal
            driver.switch_to.window(driver.window_handles[0])

    return master_df


# Set up the WebDriver
driver = webdriver.Firefox()
os.system("clear")

# Marcar el tiempo de inicio
start_time = time.time()

try:
    # Open the main webpage
    driver.get("https://www.airbnb.com.co/s/Bogot%C3%A1--Colombia/homes")
    
    # Esperar 3 segundos para que la página se cargue completamente
    wait_for_page_load(3)
    
    # Extraer los primeros enlaces de los botones de la página principal
    starting_links = extract_next_links()


    # Navegar y extraer datos en grupos de pestañas
    master_df = extract_data_in_groups(starting_links, group_size=3, max_pages=15)

    # Mostrar las dimensiones del DataFrame
    print(f"\nDimensiones del DataFrame: {master_df.shape}")

    # Identificar datos duplicados (duplicados completos)
    duplicates = master_df[master_df.duplicated()]
    num_duplicates = duplicates.shape[0]
    print(f"\nDatos duplicados encontrados: {num_duplicates}")

    # Exportar a JSON con UTF-8 y caracteres especiales correctamente
    output_filename = "airbnb_listings.json"
    with open(output_filename, 'w', encoding='utf-8') as json_file:
        json.dump(master_df.to_dict(orient='records'), json_file, ensure_ascii=False, indent=4)

    # Mostrar la ruta del archivo JSON
    file_path = os.path.join(os.getcwd(), output_filename)
    print(f"\nDatos exportados a: {file_path}")

finally:
    driver.quit()

    # Calcular y mostrar el tiempo total transcurrido
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"\nTiempo total de ejecución: {elapsed_time:.2f} segundos")
