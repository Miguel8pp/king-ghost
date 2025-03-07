from pymongo import MongoClient
from urllib.parse import quote_plus

# Datos de conexión (escapamos el nombre de usuario y la contraseña)
username = "Ghot88"
password = "@MyS@1210"  # Asegúrate de tener la contraseña correcta
encoded_username = quote_plus(username)
encoded_password = quote_plus(password)

# Conexión a la base de datos (URI con las credenciales escapadas)
uri = f"mongodb+srv://{encoded_username}:{encoded_password}@cluster0.hx8un.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)

# Conexión a la base de datos
db = client['db1']
collection = db['usuarios']

# Encontrar todos los documentos y actualizar el campo 'saldo'
for user in collection.find():
    saldo = user.get('saldo', '0')  # Si no tiene saldo, le asignamos '0' por defecto
    print(f"Saldo de {user['usuario']}: {saldo}")  # Imprimir el saldo actual
    if isinstance(saldo, str):
        try:
            # Convertimos el saldo de string a float
            nuevo_saldo = float(saldo)
            # Actualizamos el campo 'saldo'
            collection.update_one({'_id': user['_id']}, {'$set': {'saldo': nuevo_saldo}})
            print(f"Actualizado saldo del usuario {user['usuario']} a {nuevo_saldo}")
        except ValueError:
            print(f"Saldo no convertible para el usuario {user['usuario']}")
