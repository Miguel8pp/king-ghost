import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Api:
    def __init__(self):
        # URL de la API de Yoursmm (ahora desde las variables de entorno)
        self.api_url = os.getenv('YOURSMM_API_URL', 'https://yoursmm.net/api/v2')  # Valor por defecto en caso de no encontrar la variable
        
        # Cargar la clave de la API desde las variables de entorno
        self.api_key = os.getenv('YOURSMM_API_KEY')  # Se obtiene la clave de la API desde el archivo .env
        
        if not self.api_key:
            raise ValueError("API Key no encontrada. Asegúrate de tener la variable 'YOURSMM_API_KEY' en el archivo .env")

    def _connect(self, params):
        """
        Realiza la conexión a la API usando los parámetros proporcionados.
        """
        params['key'] = self.api_key  # Se asegura de agregar la API key a la solicitud.
        
        try:
            # Realizamos la solicitud POST a la API
            response = requests.post(self.api_url, data=params)
            response.raise_for_status()  # Si la respuesta tiene un código de error HTTP, se lanza una excepción.
            
            # Si la respuesta es exitosa (código 200), se devuelve el resultado en formato JSON.
            return response.json()
        except requests.exceptions.RequestException as e:
            # Si ocurre un error en la solicitud, lo manejamos adecuadamente.
            return {"error": f"Error de conexión: {e}"}

    def services(self):
        """
        Obtiene los servicios disponibles desde la API de Yoursmm.
        """
        return self._connect({
            'action': 'services'
        })

    def categories(self):
        """
        Obtiene las categorías de servicios disponibles desde la API de Yoursmm y las organiza en un set único.
        """
        services = self.services()  # Obtener los servicios desde la API
        if services and isinstance(services, list):
            # Crear un set para almacenar categorías únicas
            categories = set()
            for service in services:
                categories.add(service['category'])  # Agregar la categoría a la lista de categorías
            return list(categories)  # Devolver las categorías como lista
        return {"error": "No se pudieron obtener las categorías."}
    
    def balance(self):
        """
        Obtiene el saldo disponible del usuario.
        """
        return self._connect({
            'action': 'balance'
        })
    
    def get_order_status(self, order_id):
        """
        Obtiene el estado de un pedido usando el ID del pedido.
        """
        return self._connect({
            'action': 'status',
            'order': order_id
        })

    def order(self, order_data):
        """
        Realiza un pedido de acuerdo a los datos proporcionados.
        """
        return self._connect({
            'action': 'order',
            'service': order_data['service'],
            'link': order_data['link'],
            'quantity': order_data['quantity']
        })
