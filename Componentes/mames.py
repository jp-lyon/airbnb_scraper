import requests
import re

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
                lat = p_lat.findall(r.text)[0]
                lon = p_lon.findall(r.text)[0]
                success = True
                return float(lat), float(lon)
            except Exception as e:
                print(f'No hay coordenada, intento número: {attempts + 1}')
                print(f'Error: {e}')
                attempts += 1
        return 0.0, 0.0
