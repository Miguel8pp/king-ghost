from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer as Serializer
from dotenv import load_dotenv  # Importar la librería dotenv
import os  # Para acceder a las variables de entorno
from urllib.parse import quote_plus  # Importar quote_plus
import requests  # Para hacer peticiones HTTP a la API de Yoursmm
import datetime

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
db = client['db1']  # Base de datos
collection = db['usuarios']  # Colección de usuarios
pedidos_collection = db['pedidos']  # Colección de pedidos

# Configuración de SendGrid
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

# Crear una instancia de Flask
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Clave secreta para sesiones
app.secret_key = "advpjsh"

# Función para enviar correos
def enviar_email(destinatario, asunto, cuerpo):
    mensaje = Mail(
        from_email='kinghostshop88@gmail.com',  # Cambia esto por tu correo
        to_emails=destinatario,
        subject=asunto,
        html_content=cuerpo
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)  # Usa tu clave API de SendGrid
        response = sg.send(mensaje)
        print(f"Correo enviado con éxito! Status code: {response.status_code}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

# Función para enviar correo de bienvenida
def enviar_correo_bienvenida(email, usuario):
    asunto = "Bienvenido a nuestra plataforma"
    cuerpo = f"""
    <p>Hola {usuario},</p>
    <p>Gracias por registrarte en nuestra plataforma. Estamos felices de tenerte con nosotros.</p>
    <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>
    <p>¡Disfruta de tu experiencia!</p>
    """
    enviar_email(email, asunto, cuerpo)

# Función para obtener el saldo del usuario
def obtener_saldo(usuario):
    user_data = collection.find_one({'usuario': usuario})
    saldo = user_data.get('saldo', 0)  # Retorna el saldo, si no existe, 0 por defecto
    return float(saldo)  # Asegurarse de que el saldo es un número flotante

@app.route('/')
def home():
    return redirect(url_for('pagina_principal'))  # Redirige a la página principal

@app.route('/pagina_principal')
def pagina_principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Obtener el saldo del usuario
    saldo = obtener_saldo(session['usuario'])
    
    # Obtener los servicios disponibles desde Yoursmm
    api = Api()
    services = api.services()
    
    return render_template('index.html', usuario=session['usuario'], saldo=saldo, services=services)

@app.route('/agregar_orden', methods=['GET', 'POST'])
def agregar_orden():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    saldo = obtener_saldo(usuario)

    if request.method == 'POST':
        cantidad = int(request.form['quantity'])
        monto = (cantidad * 10) / 1000  # Calcular el monto por cantidad

        # Obtener el ID del servicio directamente desde el campo de texto
        servicio_id = request.form['service']
        enlace = request.form['link']  # URL del enlace

        # Validar si el saldo es suficiente
        if saldo >= monto:
            # Crear el pedido en Yoursmm
            api = Api()
            order_data = {
                'service': servicio_id,  # ID del servicio
                'link': enlace,  # URL del enlace
                'quantity': cantidad,  # Cantidad de acciones
            }

            order_response = api.order(order_data)

            if order_response:
                # Guardar el pedido en la colección de MongoDB
                pedidos_collection.insert_one({
                    'usuario': usuario,
                    'cantidad': cantidad,
                    'monto': monto,
                    'estado': 'Pendiente',
                    'fecha': datetime.datetime.now()
                })

                # Actualizar el saldo del usuario
                collection.update_one({'usuario': usuario}, {'$inc': {'saldo': -monto}})

                flash("Pedido creado con éxito. Puedes hacer otro pedido.", "success")
            else:
                flash("Hubo un problema al crear el pedido con Yoursmm. Intenta nuevamente.", "error")
        else:
            flash("No tienes suficiente saldo para realizar esta orden.", "error")
            return render_template('yoursmm.html', usuario=usuario, saldo=saldo)

    return render_template('yoursmm.html', usuario=usuario, saldo=saldo)

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

        # Hashear la contraseña
        hashed_password = bcrypt.generate_password_hash(contrasena).decode('utf-8')

        # Insertar usuario en la base de datos
        collection.insert_one({
            'usuario': usuario,
            'email': email,
            'contrasena': hashed_password,
            'saldo': 0
        })
        
        session['usuario'] = usuario

        # Enviar correo de bienvenida
        enviar_correo_bienvenida(email, usuario)

        return redirect(url_for('pagina_principal'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        # Buscar al usuario en la base de datos
        user = collection.find_one({'usuario': usuario})
        
        # Verificar si las credenciales son correctas
        if user and bcrypt.check_password_hash(user['contrasena'], contrasena):
            session['usuario'] = usuario
            return redirect(url_for('pagina_principal'))
        else:
            flash("Usuario o contraseña incorrectos.")
            return render_template('login.html')

    return render_template('login.html')

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

@app.route('/mi_perfil')
def mi_perfil():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
    return render_template('mi_perfil.html', usuario=user_data['usuario'], email=user_data['email'])

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
