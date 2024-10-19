import folium
from folium.plugins import Draw
from flask import Flask, request, jsonify
import threading
import webbrowser

# Crear un servidor Flask para manejar la interacción y obtener las coordenadas
app = Flask(__name__)

@app.route('/')
def index():
    # Centro inicial del mapa (Bogotá)
    center_lat = 4.7110
    center_lng = -74.0721
    mapa = folium.Map(location=[center_lat, center_lng], zoom_start=13)

    # Agregar herramienta de dibujo
    draw = Draw(export=False)  # Desactivar la exportación automática
    draw.add_to(mapa)

    # Guardar el mapa en un archivo HTML
    mapa.save("interactive_bounding_box.html")
    return mapa._repr_html_()

# Ruta para recibir coordenadas desde el cliente
@app.route('/coordenadas', methods=['POST'])
def coordenadas():
    data = request.get_json()  # Recibe los datos enviados desde el cliente
    print("Coordenadas recibidas del rectángulo:")
    
    # Verifica si los datos contienen las coordenadas
    if data and 'geometry' in data and 'coordinates' in data['geometry']:
        coords = data['geometry']['coordinates'][0]  # Extraer las coordenadas

        # Formatear y mostrar las coordenadas de forma legible
        print("\nCoordenadas del bounding box (formato legible):")
        for i, coord in enumerate(coords):
            print(f"Vértice {i+1}: Latitud: {coord[1]}, Longitud: {coord[0]}")
    else:
        print("No se encontraron coordenadas en los datos recibidos.")
    
    return jsonify({'status': 'success'})

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

# Iniciar el servidor en un hilo separado para abrir el navegador automáticamente
if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(port=5000)
