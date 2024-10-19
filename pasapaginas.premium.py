import os
import json
import time
import random
import pandas as pd
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
    # DataFrames para manejar los enlaces visitados y enlaces por visitar
    df_visited_links = pd.DataFrame(columns=['link', 'visited'])
    df_pending_links = pd.DataFrame(columns=['link', 'visited'])
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

                # Verifica si el enlace ya ha sido visitado o está pendiente de ser visitado
                if ((not df_visited_links.empty and (df_visited_links['link'] == url_json).any()) or
                    (not df_pending_links.empty and (df_pending_links['link'] == url_json).any())):
                    continue

                # Inicializa los enlaces por visitar para esta página
                df_pending_links = pd.concat([pd.DataFrame({'link': [url_json], 'visited': [False]}), df_pending_links], ignore_index=True)

                # Procesa los enlaces en df_pending_links
                while not df_pending_links[df_pending_links['visited'] == False].empty:
                    current_link = df_pending_links[df_pending_links['visited'] == False].iloc[0]['link']

                    # Verifica nuevamente si el enlace ya fue visitado
                    if (not df_visited_links.empty and (df_visited_links['link'] == current_link).any()):
                        df_pending_links.loc[df_pending_links['link'] == current_link, 'visited'] = True
                        continue

                    # Abre el enlace
                    driver.get(current_link)
                    wait_for_page_load(3)
                    total_link_counter += 1

                    # Extrae nuevos enlaces de la página actual
                    wait = WebDriverWait(driver, 5)
                    try:
                        buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "c1ackr0h")))
                        for button in buttons:
                            link = button.get_attribute("href")
                            if link and (not df_visited_links.empty and not (df_visited_links['link'] == link).any()) and not (df_pending_links['link'] == link).any():
                                df_pending_links = pd.concat([pd.DataFrame({'link': [link], 'visited': [False]}), df_pending_links], ignore_index=True)
                    except TimeoutException:
                        pass

                    # Marcar el enlace actual como visitado y mover al DataFrame de visitados
                    df_pending_links.loc[df_pending_links['link'] == current_link, 'visited'] = True
                    df_visited_links = pd.concat([pd.DataFrame({'link': [current_link], 'visited': [True]}), df_visited_links], ignore_index=True)

    print("Todos los enlaces de la pagina han sido visitados.")

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
