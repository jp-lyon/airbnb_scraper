import time
import logging
import psutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import requests
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver import ActionChains


def setup_webdriver():
    options = Options()
    options.headless = True

    profile = webdriver.FirefoxProfile()
    profile.set_preference("permissions.default.image", 2)
    profile.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", "false")
    options.profile = profile

    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)

    driver = webdriver.Firefox(options=options)
    return driver



def scroll_container(driver):
    while True:
        try:
            time.sleep(5)
            element = driver.find_element(By.CLASS_NAME, "scrollba")
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
        except (TimeoutException, StaleElementReferenceException) as e:
            print("No more View More buttons")
        break



def extract_last_comment_date(driver, idPublication: str) -> str:
    try:
        driver.get(f'https://www.airbnb.com.co/rooms/{idPublication}/reviews')
        time.sleep(10)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
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

def main():
    driver = setup_webdriver()
    try:
        last_comment = extract_last_comment_date(driver, "1032001630490013997")
        print(f"Fecha del último comentario: {last_comment}")
    finally:
        driver.quit()
        print("WebDriver cerrado correctamente")

if __name__ == "__main__":
    main()