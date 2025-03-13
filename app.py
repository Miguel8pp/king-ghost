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
from bson import Decimal128  # Cambiar esta línea
from decimal import Decimal  # Asegúrate de mantener Decimal si lo necesitas

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
pedidos_collection = db['Pedidos']  # Cambio realizado aquí: 'pedidos' por 'Pedidos'

# Configuración de SendGrid
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

# Crear una instancia de Flask
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Clave secreta para sesiones
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'advpjsh')  # Asegúrate de usar un valor secreto en producción

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
    saldo = user_data.get('saldo', 0)  # Devolver saldo o 0 si no existe
    # Convertir Decimal128 a float si es necesario
    if isinstance(saldo, Decimal128):
        saldo = float(saldo.to_decimal())  # Convertir Decimal128 a Decimal y luego a float
    elif isinstance(saldo, Decimal):
        saldo = float(saldo)  # Convertir Decimal a float
    return saldo

# Ruta principal que requiere estar logueado
@app.route('/pagina_principal')
def pagina_principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    saldo = obtener_saldo(session['usuario'])
    api = Api()
    categories = api.categories()  # Obtener categorías
    services = api.services()  # Obtener servicios

    # Imprimir la respuesta para ver su estructura
    print("Categorías:", categories)
    print("Servicios:", services)

    # Verificar si la respuesta es un diccionario y tiene la clave 'categories'
    if isinstance(categories, dict) and 'categories' in categories:
        categories = categories['categories']
    else:
        categories = []  # Si no tiene la clave 'categories', asignamos una lista vacía

    if isinstance(services, dict) and 'services' in services:
        services = services['services']
    else:
        services = []  # Si no tiene la clave 'services', asignamos una lista vacía

    return render_template('index.html', usuario=session['usuario'], saldo=saldo, categories=categories, services=services)

# Ruta para agregar una orden
@app.route('/agregar_orden', methods=['GET', 'POST'])
def agregar_orden():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    saldo = obtener_saldo(usuario)

    # Verificar que el saldo sea al menos 1 dólar
    if saldo < 1:
        flash("No tienes suficiente saldo para realizar un pedido. Tu saldo debe ser al menos 1 dólar.", "error")
        return render_template('yoursmm.html', usuario=usuario, saldo=saldo)

    # Obtener categorías y servicios de la API
    api = Api()
    categories = api.categories()  # Obtener categorías
    services = api.services()  # Obtener servicios

    if request.method == 'POST':
        cantidad = int(request.form['quantity'])
        servicio_id = request.form['service']
        enlace = request.form['link']  # URL del enlace

        # Obtener detalles del servicio seleccionado
        servicio = next((s for s in services if s['id'] == servicio_id), None)

        if servicio:
            # En este caso no utilizamos el monto mínimo ni máximo, solo la cantidad
            precio_por_unidad = servicio.get('price', 0)  # Precio del servicio por unidad

            # Calcular el monto total por la cantidad seleccionada
            monto = (cantidad * precio_por_unidad) / 1000  # Este cálculo depende del precio del servicio

            if saldo >= monto:
                # Crear el pedido en Yoursmm
                order_data = {
                    'service': servicio_id,  # ID del servicio
                    'link': enlace,  # URL del enlace
                    'quantity': cantidad,  # Cantidad de acciones
                }

                try:
                    order_response = api.order(order_data)

                    if order_response and 'order' in order_response:  # Cambié 'order_id' por 'order'
                        # Obtener el estado del pedido desde la API de Yoursmm
                        order_id = order_response['order']  # Usamos 'order' aquí
                        estado = api.get_order_status(order_id)  # Suponiendo que la API tenga este método

                        # Guardar el pedido en la colección de MongoDB
                        pedidos_collection.insert_one({
                            'usuario': usuario,
                            'cantidad': cantidad,
                            'monto': monto,
                            'estado': estado,  # Guardamos el estado obtenido
                            'order_id': order_id,  # Guardar el ID de la orden de la API
                            'fecha': datetime.datetime.now()  # Aseguramos que la fecha esté registrada
                        })

                        # Actualizar el saldo del usuario
                        collection.update_one({'usuario': usuario}, {'$inc': {'saldo': -monto}})

                        flash("Pedido creado con éxito. Puedes hacer otro pedido.", "success")
                    else:
                        flash(f"Hubo un problema al crear el pedido", "error")
                except Exception as e:
                    print(f"Error al realizar el pedido {e}")
                    flash("Error al realizar el pedido. Intenta más tarde.", "error")
            else:
                flash("No tienes suficiente saldo para realizar esta orden.", "error")
                return render_template('yoursmm.html', usuario=usuario, saldo=saldo)

    return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services)

# Ruta para mostrar los pedidos del usuario
@app.route('/pedidos')
def pedidos():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    usuario = session['usuario']
    saldo = obtener_saldo(usuario)  # Obtenemos el saldo del usuario

    # Obtener solo los pedidos del usuario logueado
    pedidos_usuario = pedidos_collection.find({'usuario': usuario}).sort('fecha', -1)  # Obtener pedidos del usuario

    # Convertir la fecha en cada pedido a un formato legible
    pedidos_usuario = list(pedidos_usuario)  # Convertir a lista para poder iterar correctamente
    for pedido in pedidos_usuario:
        if 'fecha' in pedido:
            pedido['fecha'] = pedido['fecha'].strftime('%Y-%m-%d %H:%M:%S')  # Formatear la fecha
        else:
            pedido['fecha'] = 'Fecha no disponible'  # Si no hay fecha, asignar un valor predeterminado

    # Pasamos los pedidos y el saldo al template
    return render_template('pedidos.html', pedidos=pedidos_usuario, saldo=saldo)

# Ruta para registrar un nuevo usuario
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        usuario = request.form['usuario']
        email = request.form['email']
        contrasena = request.form['contrasena']

        # Verificar si el correo ya está registrado
        if collection.find_one({'email': email}):
            flash("El correo electrónico ya está registrado.")
            return redirect(url_for('registro'))

        # Generar el hash de la contraseña
        hashed_password = bcrypt.generate_password_hash(contrasena).decode('utf-8')

        # Insertar el usuario en la base de datos con saldo 0.0000000
        collection.insert_one({
            'usuario': usuario,
            'email': email,
            'contrasena': hashed_password,
            'saldo': 0.0000000  # Aquí asignamos el saldo inicial de 0.0000000
        })
        
        # Iniciar sesión automáticamente después de registrarse
        session['usuario'] = usuario

        # Enviar correo de bienvenida
        enviar_email(email, "Bienvenido a nuestra plataforma", f"Hola {usuario}, ¡bienvenido a nuestra plataforma! para agregar fondos a su cuenta comuníquese por WhatsApp al número +52 4661002589")

        # Redirigir al usuario a la página principal
        return redirect(url_for('pagina_principal'))

    return render_template('register.html')

# Ruta para el login de usuarios
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena'] 

        user = collection.find_one({'usuario': usuario})
        
        if user and bcrypt.check_password_hash(user['contrasena'], contrasena):
            session['usuario'] = usuario
            return redirect(url_for('pagina_principal'))
        else:
            flash("Usuario o contraseña incorrectos.")
            return render_template('login.html')

    return render_template('login.html')

# Ruta para recuperar contraseña
@app.route('/recuperar_contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        email = request.form['email']
        usuario = collection.find_one({'email': email})

        if usuario:
            token = serializer.dumps(email, salt='password-reset-salt')
            enlace = url_for('restablecer_contrasena', token=token, _external=True)
            asunto = "Recuperación de contraseña"
            cuerpo = f"""
            <p>Hola, hemos recibido una solicitud para restablecer tu contraseña.</p>
            <p>Si no has solicitado este cambio, ignora este mensaje.</p>
            <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
            <a href="{enlace}">Restablecer contraseña</a>
            """
            enviar_email(email, asunto, cuerpo)
            flash("Te hemos enviado un correo para recuperar tu contraseña.", "success")
        else:
            flash("El correo electrónico no está registrado.", "error")

    return render_template('recuperar_contrasena.html')

# Ruta para restablecer la contraseña
@app.route('/restablecer_contrasena/<token>', methods=['GET', 'POST'])
def restablecer_contrasena(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash("El enlace de restablecimiento ha caducado o es inválido.", "error")
        return redirect(url_for('recuperar_contrasena'))

    if request.method == 'POST':
        nueva_contrasena = request.form['nueva_contrasena']
        hashed_password = bcrypt.generate_password_hash(nueva_contrasena).decode('utf-8')
        collection.update_one({'email': email}, {'$set': {'contrasena': hashed_password}})
        flash("Tu contraseña ha sido restablecida con éxito.", "success")
        return redirect(url_for('login'))

    return render_template('restablecer_contrasena.html')

# Ruta para mostrar el perfil del usuario
@app.route('/mi_perfil')
def mi_perfil():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
    return render_template('mi_perfil.html', usuario=user_data['usuario'], email=user_data['email'])

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
