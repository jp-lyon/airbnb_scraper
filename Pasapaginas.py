import os
import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
)
from selenium.webdriver.firefox.options import Options

# Función para esperar un tiempo específico
def wait_for_page_load(seconds):
    time.sleep(seconds)

# Función para navegar por las páginas
def navigate_pages(driver, json_files):
    # Lista global de enlaces visitados para todas las páginas
    global_visited_links = set()
    total_link_counter = 0

    # Para cada archivo JSON
    for json_file in json_files:
        with open(json_file, 'r') as file:
            lines = file.readlines()
            random.shuffle(lines)
            # Para cada URL en el archivo JSON
            for line in lines:
                data = json.loads(line.strip())
                url_json = data['url']

                # Verifica si el enlace ya ha sido visitado
                if url_json in global_visited_links:
                    continue

                # Inicializa los enlaces visitados y por visitar para esta página
                page_visited_links = set()
                page_links_to_visit = []

                # Agrega la URL inicial a los enlaces a visitar
                page_links_to_visit.append(url_json)

                # Procesa los enlaces en page_links_to_visit
                while page_links_to_visit:
                    current_link = page_links_to_visit.pop(0)
                    if current_link in page_visited_links or current_link in global_visited_links:
                        continue

                    # Abre el enlace
                    driver.get(current_link)
                    input("Presiona Enter para continuar a la siguiente página...")
                    os.system("clear")
                    wait_for_page_load(3)
                    total_link_counter += 1

                    # Extrae nuevos enlaces de la página actual
                    wait = WebDriverWait(driver, 5)
                    buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "c1ackr0h")))
                    for button in buttons:
                        link = button.get_attribute("href")
                        if link and (link not in page_links_to_visit or link in page_visited_links):
                            page_links_to_visit.append(link)

                    # Agrega el enlace actual a los enlaces visitados
                    page_visited_links.add(current_link)
                    global_visited_links.add(current_link)

if __name__ == "__main__":
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options)
    os.system("clear")

    json_files = [
        "/home/jjleo/Entorno/Python/airbnb_scraper/airbnb_urls_bogota_zoom_14.json"
    ]

    try:
        navigate_pages(driver, json_files)
    finally:
        driver.quit()
