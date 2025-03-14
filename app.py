from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus
import requests
import datetime
from bson import Decimal128
from decimal import Decimal

# Importar el archivo yoursmm.py
from yoursmm import Api

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Conexión a MongoDB Atlas
username = os.getenv('MONGO_USERNAME')
password = os.getenv('MONGO_PASSWORD')
username = quote_plus(username)
password = quote_plus(password)
client = MongoClient(f"mongodb+srv://{username}:{password}@cluster0.hx8un.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['db1']
collection = db['usuarios']
pedidos_collection = db['Pedidos']

# Configuración de SendGrid
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

# Crear una instancia de Flask
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Clave secreta para sesiones
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'advpjsh')

# Crear el serializer para generar y verificar tokens
serializer = URLSafeTimedSerializer(app.secret_key)

# Función para enviar correos
def enviar_email(destinatario, asunto, cuerpo):
    mensaje = Mail(
        from_email='kinghostshop88@gmail.com',
        to_emails=destinatario,
        subject=asunto,
        html_content=cuerpo
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(mensaje)
        print(f"Correo enviado con éxito! Revisa los correos de spam! Status code: {response.status_code}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        flash("Error al enviar el correo, inténtalo más tarde.", "error")

# Función para obtener el saldo del usuario
def obtener_saldo(usuario):
    user_data = collection.find_one({'usuario': usuario})
    saldo = user_data.get('saldo', 0)
    if isinstance(saldo, Decimal128):
        saldo = float(saldo.to_decimal())
    elif isinstance(saldo, Decimal):
        saldo = float(saldo)
    return saldo

# Ruta principal
@app.route('/pagina_principal')
def pagina_principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    saldo = obtener_saldo(session['usuario'])
    api = Api()
    categories = api.categories()
    services = api.services()

    if isinstance(categories, dict) and 'categories' in categories:
        categories = categories['categories']
    else:
        categories = []

    if isinstance(services, dict) and 'services' in services:
        services = services['services']
    else:
        services = []

    return render_template('index.html', usuario=session['usuario'], saldo=saldo, categories=categories, services=services)

# Ruta para agregar una orden
@app.route('/agregar_orden', methods=['GET', 'POST'])
def agregar_orden():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    saldo = obtener_saldo(usuario)

    if saldo < 1:
        flash("No tienes suficiente saldo para realizar un pedido. Tu saldo debe ser al menos 1 dólar.", "error")
        return render_template('yoursmm.html', usuario=usuario, saldo=saldo)

    api = Api()
    categories = api.categories()
    services = api.services()

    if request.method == 'POST':
        cantidad = int(request.form['quantity'])
        servicio_id = request.form['service']
        enlace = request.form['link']

        # Obtener el servicio correspondiente
        servicio = next((s for s in services if s['service'] == servicio_id), None)

        if servicio:
            precio_por_unidad = float(servicio.get('rate', 0)) * 1.40  # Aumento del 40%

            monto = (cantidad * precio_por_unidad) / 1000

            if saldo >= monto:
                order_data = {
                    'service': servicio_id,
                    'link': enlace,
                    'quantity': cantidad,
                }

                try:
                    order_response = api.order(order_data)

                    if order_response and 'order' in order_response:
                        order_id = order_response['order']
                        estado = api.get_order_status(order_id)

                        pedidos_collection.insert_one({
                            'usuario': usuario,
                            'cantidad': cantidad,
                            'monto': monto,
                            'estado': estado,
                            'order_id': order_id,
                            'fecha': datetime.datetime.now()
                        })

                        collection.update_one({'usuario': usuario}, {'$inc': {'saldo': -monto}})

                        flash("Pedido creado con éxito. Puedes hacer otro pedido.", "success")
                    else:
                        flash(f"Hubo un problema al crear el pedido", "error")
                except Exception as e:
                    print(f"Error al realizar el pedido {e}")
                    flash("Error al realizar el pedido. Intenta más tarde.", "error")
            else:
                flash("No tienes suficiente saldo para realizar esta orden.", "error")
                
        # Redirigir después de procesar el formulario (PRG)
        return redirect(url_for('agregar_orden'))

    return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services)

# Ruta de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('pagina_principal'))

    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['password']
        
        user_data = collection.find_one({'usuario': username})
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            session['usuario'] = username
            flash("Bienvenido de nuevo!", "success")
            return redirect(url_for('pagina_principal'))
        else:
            flash("Usuario o contraseña incorrectos. Intenta de nuevo.", "error")

    return render_template('login.html')

# Ruta de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if 'usuario' in session:
        return redirect(url_for('pagina_principal'))

    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['password']
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        # Verificar si el usuario ya existe
        if collection.find_one({'usuario': username}):
            flash("El nombre de usuario ya está en uso.", "error")
            return render_template('registro.html')

        # Crear el nuevo usuario
        collection.insert_one({'usuario': username, 'password': password_hash, 'saldo': 0.0})
        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template('registro.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash("Has cerrado sesión con éxito.", "info")
    return redirect(url_for('login'))

# Ruta para el perfil del usuario
@app.route('/perfil')
def perfil():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
    return render_template('perfil.html', usuario=usuario, saldo=user_data.get('saldo', 0))

# Ruta para cambiar la contraseña
@app.route('/cambiar_contraseña', methods=['GET', 'POST'])
def cambiar_contraseña():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        usuario = session['usuario']
        nueva_contraseña = request.form['nueva_contraseña']
        nueva_contraseña_hash = bcrypt.generate_password_hash(nueva_contraseña).decode('utf-8')

        collection.update_one({'usuario': usuario}, {'$set': {'password': nueva_contraseña_hash}})
        flash("Contraseña actualizada con éxito.", "success")
        return redirect(url_for('perfil'))

    return render_template('cambiar_contraseña.html')

# Ruta para ver el historial de pedidos
@app.route('/historial_pedidos')
def historial_pedidos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    pedidos = pedidos_collection.find({'usuario': usuario})
    return render_template('historial_pedidos.html', usuario=usuario, pedidos=pedidos)

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
