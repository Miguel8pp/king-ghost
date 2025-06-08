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
from bson import ObjectId
from flask import Flask, send_from_directory
from flask import Flask, request, send_file
import subprocess
import yt_dlp
from urllib.parse import urlparse, parse_qs
import traceback
import uuid
import tempfile
import shutil
from urllib.parse import unquote_plus
import re
from werkzeug.utils import secure_filename
from bson import ObjectId
import gridfs
from io import BytesIO
import qrcode
import io









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

# Base de datos y colecciones
db = client['db1']
collection = db['usuarios']
pedidos_collection = db['Pedidos']
pagos_collection = db['Pagos'] 
posts = db["articulos"]

# GridFS
fs = gridfs.GridFS(db)      

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
        print(f"Correo enviado con éxito! Status code: {response.status_code}")
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

@app.route("/")
def inicios():
    posts_list = posts.find()  # Obtén los artículos desde la base de datos
    return render_template('inicio.html', posts=posts_list)

# Extensiones de archivo permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Verifica si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/mi_perfil', methods=['GET', 'POST'])
def mi_perfil():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})

    if request.method == 'POST':
        # Cambiar contraseña
        if 'change-password' in request.form:
            current_password = request.form['current-password']
            new_password = request.form['new-password']
            confirm_new_password = request.form['confirm-new-password']

            if not bcrypt.check_password_hash(user_data['contrasena'], current_password):
                flash("Contraseña actual incorrecta.", "error")
            elif new_password != confirm_new_password:
                flash("Las contraseñas no coinciden.", "error")
            else:
                hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                collection.update_one({'usuario': usuario}, {'$set': {'contrasena': hashed_password}})
                flash("Contraseña cambiada con éxito.", "success")

        # Cambiar correo
        if 'change-email' in request.form:
            new_email = request.form['new-email']
            current_password_email = request.form['current-password-email']

            if not bcrypt.check_password_hash(user_data['contrasena'], current_password_email):
                flash("Contraseña incorrecta.", "error")
            elif collection.find_one({'email': new_email}):
                flash("Este correo electrónico ya está registrado.", "error")
            else:
                collection.update_one({'usuario': usuario}, {'$set': {'email': new_email}})
                flash("Correo electrónico cambiado con éxito.", "success")

        # Cambiar foto de perfil con GridFS
        if 'change-photo' in request.form and 'foto' in request.files:
            file = request.files['foto']
            if file and allowed_file(file.filename):
                # Eliminar foto anterior si existía
                if user_data.get('foto_id'):
                    try:
                        fs.delete(ObjectId(user_data['foto_id']))  # Eliminar la foto anterior
                    except Exception as e:
                        print(f"Error al eliminar la foto anterior: {e}")

                # Guardar nueva imagen en GridFS
                file_id = fs.put(file, filename=file.filename, content_type=file.content_type)
                collection.update_one({'usuario': usuario}, {'$set': {'foto_id': file_id}})
                session['foto_id'] = str(file_id)  # Guardar el nuevo foto_id en la sesión
                flash("Foto de perfil actualizada.", "success")
            else:
                flash("Formato de imagen no permitido. Usa PNG, JPG, JPEG o GIF.", "error")

        return redirect(url_for('mi_perfil'))

    foto_id = user_data.get('foto_id')
    session['foto_id'] = str(foto_id) if foto_id else None

    return render_template('mi_perfil.html', usuario=user_data['usuario'], email=user_data['email'], foto_id=foto_id)

@app.route('/foto_perfil/<foto_id>')
def foto_perfil(foto_id):
    try:
        # Obtener la foto desde GridFS usando el foto_id
        file = fs.get(ObjectId(foto_id))
        return send_file(BytesIO(file.read()), mimetype=file.content_type)
    except Exception as e:
        print(f"Error al obtener la foto: {e}")
        # Imagen por defecto si no existe o hay un error
        return send_file('static/fotos_perfil/default.jpg', mimetype='image/jpeg')

# Ruta principal
@app.route('/pagina_principal')
def pagina_principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Verificar si el usuario está baneado
    user_data = collection.find_one({'usuario': session['usuario']})
    if user_data.get('ban') == 'ban':
        razon_ban = user_data.get('razon_ban', 'Razón no especificada')
        return render_template('ban.html', razon_ban=razon_ban)  # Pasamos la razón del ban a la plantilla

    saldo = obtener_saldo(session['usuario'])
    api = Api()
    categories = api.categories()
    services = api.services()
    foto_id = user_data.get('foto_id')

    # Validación para categories y services
    if isinstance(categories, dict) and 'categories' in categories:
        categories = categories['categories']
    else:
        categories = []  # Asegúrate de que categories siempre sea una lista válida

    if isinstance(services, dict) and 'services' in services:
        services = services['services']
    else:
        services = []  # Asegúrate de que services siempre sea una lista válida

    # Limpiar valores None en categories y services
    categories = [category for category in categories if category is not None and isinstance(category, dict)]
    services = [service for service in services if service is not None and isinstance(service, dict)]
    
    return render_template('index.html', usuario=session['usuario'], saldo=saldo, categories=categories, services=services, foto_id=foto_id)

# Ruta para crear orden de pago
@app.route('/saldo', methods=['GET', 'POST'])
def saldo():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirigir a login si no hay usuario en la sesión

    # Obtener el usuario desde la sesión
    usuario = session['usuario']

    # Obtener datos actualizados del usuario desde MongoDB
    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')

    saldo = obtener_saldo(usuario)

    if request.method == 'POST':
        # Aquí manejamos el pago
        try:
            monto = float(request.form['monto'])  # Monto a agregar
            metodo_pago = request.form['metodo_pago']  # Método de pago seleccionado (PayPal, Binance, etc.)

            # Guardar la orden de pago en la base de datos (colección Pagos)
            pagos_collection.insert_one({
                'usuario': usuario,
                'monto': monto,
                'metodo_pago': metodo_pago,
                'estado': 'pendiente',  # El estado inicial será 'pendiente'
                'fecha': datetime.datetime.now()
            })

            flash("Pago guardado correctamente. El estado es 'pendiente'.", "success")
            return redirect(url_for('saldo'))

        except Exception as e:
            flash(f"Hubo un error al procesar tu pago: {e}", "error")
            return redirect(url_for('saldo'))

    # Renderizar la plantilla de saldo con el saldo del usuario y el foto_id
    return render_template('saldo.html', usuario=usuario, saldo=saldo, foto_id=foto_id)


@app.route('/guardar_pago', methods=['POST'])
def guardar_pago():
    try:
        # Obtener los datos del pago desde el frontend (en formato JSON)
        data = request.get_json()

        # Extraer datos del pago
        usuario = data['usuario']
        monto = data['monto']
        metodo_pago = data['metodo_pago']
        estado = data.get('estado', 'pendiente')  # 'pendiente' es el estado por defecto
        fecha = datetime.datetime.now()

        # Insertar el pago en la colección 'Pagos'
        pagos_collection.insert_one({
            'usuario': usuario,
            'monto': monto,
            'metodo_pago': metodo_pago,
            'estado': estado,
            'fecha': fecha
        })

        # Responder al frontend con éxito
        return jsonify({'success': True, 'message': 'Pago guardado exitosamente.'})

    except Exception as e:
        # En caso de error, devolver un mensaje de error
        return jsonify({'success': False, 'error': str(e)})
    
    

@app.route('/movimientos')
def movimientos():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirigir a login si no hay usuario en la sesión
    
    # Obtener el usuario desde la sesión
    usuario = session['usuario']

    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')

    # Obtener los movimientos de pagos del usuario desde la base de datos
    movimientos_usuario = pagos_collection.find({'usuario': usuario})


    # Convertir los movimientos de MongoDB en una lista de diccionarios
    pagos = []
    for pago in movimientos_usuario:
        estado = pago.get('estado', 'pendiente')

        # Asegurarnos de que 'monto' sea un número antes de redondearlo
        monto = pago.get('monto', 0)
        if isinstance(monto, (int, float)):  # Si 'monto' ya es un número, lo dejamos como está
            monto_redondeado = round(monto, 2)
        else:  # Si 'monto' es un string, tratamos de convertirlo a float
            try:
                monto_redondeado = round(float(monto), 2)
            except ValueError:
                monto_redondeado = 0  # Si no podemos convertirlo, lo dejamos como 0

        pagos.append({
            'descripcion': pago.get('metodo_pago', 'Desconocido'),
            'monto': monto_redondeado,
            'estado': estado,
            'fecha': pago.get('fecha', datetime.datetime.now()).strftime('%Y-%m-%d')
        })
    
    return render_template('mov.html', usuario=usuario, pagos=pagos, foto_id=foto_id)



# Ruta para agregar una orden
@app.route('/agregar_orden', methods=['GET', 'POST'])
def agregar_orden():
    # Verificar si el usuario está autenticado
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirige a la página de login si no está autenticado

    usuario = session['usuario']
    saldo = obtener_saldo(usuario)  # Obtener saldo del usuario

    # Si el saldo es 0 o inferior, mostrar el mensaje de "Saldo Insuficiente"
    if saldo <= 0:
        flash("Saldo Insuficiente. No tienes saldo suficiente para realizar pedidos.", "error")
        
        # Traer categorías y servicios desde la API
        api = Api()
        categories = api.categories()
        services = api.services()

        # Limpiar valores None de categories y services
        categories = [category for category in categories if category is not None]
        services = [service for service in services if service is not None]

        # Redirigir a la misma página, ya que no hay saldo suficiente
        return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services)

    # Si el saldo es suficiente, obtener categorías y servicios
    api = Api()
    categories = api.categories()
    services = api.services()

    # Limpiar valores None de categories y services
    categories = [category for category in categories if category is not None]
    services = [service for service in services if service is not None]

    # Manejar la lógica del formulario cuando se hace un POST
    if request.method == 'POST':
        cantidad = int(request.form['quantity'])  # Obtener cantidad
        servicio_id = request.form['service']  # Obtener ID del servicio
        enlace = request.form['link']  # Obtener el link

        # Buscar el servicio correspondiente en la lista de servicios
        servicio = next((s for s in services if s['service'] == servicio_id), None)

        if servicio:
            # Calcular el precio por unidad con el aumento del 40%
            precio_por_unidad = float(servicio.get('rate', 0)) * 1.40
            monto = (cantidad * precio_por_unidad) / 1000  # Calcular el monto total del pedido

            # Verificar si el saldo es suficiente para realizar el pedido
            if saldo >= monto:
                order_data = {
                    'service': servicio_id,
                    'link': enlace,
                    'quantity': cantidad,
                }

                try:
                    # Realizar el pedido a la API
                    order_response = api.order(order_data)

                    if order_response and 'order' in order_response:
                        order_id = order_response['order']
                        estado = api.get_order_status(order_id)

                        # Asegurarte de que la primera letra sea mayúscula
                        if estado and 'status' in estado:
                            estado = estado['status'].capitalize()  # Convertir la primera letra a mayúscula

                        # Registrar el pedido en la base de datos
                        pedidos_collection.insert_one({
                            'usuario': usuario,
                            'cantidad': cantidad,
                            'monto': monto,
                            'estado': estado,  # Guardar el estado con la primera letra mayúscula
                            'order_id': order_id,
                            'fecha': datetime.datetime.now()
                        })

                        # Actualizar el saldo del usuario
                        collection.update_one({'usuario': usuario}, {'$inc': {'saldo': -monto}})

                        flash("Pedido creado con éxito. Puedes hacer otro pedido.", "success")
                    else:
                        flash(f"Hubo un problema al crear el pedido: {order_response.get('error', 'Error desconocido')}", "error")
                except Exception as e:
                    flash("Error al realizar el pedido. Intenta más tarde.", "error")
            else:
                flash("No tienes suficiente saldo para realizar esta orden.", "error")

        # Redirigir después de procesar el formulario (PRG)
        return redirect(url_for('agregar_orden'))

    # Si es un GET, simplemente renderizar la página con las categorías y servicios
    return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services)

# Ruta de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya está logueado, redirigimos a la página correspondiente
    if 'usuario' in session:
        user_data = collection.find_one({'usuario': session['usuario']})
        if user_data:
            # Si el usuario está baneado, lo redirigimos a la página de baneo
            if user_data.get('ban') == 'ban':
                razon_ban = user_data.get('razon_ban', 'Razón no especificada')
                return render_template('ban.html', razon_ban=razon_ban)  # Redirigimos a la página de baneo con la razón
            # Si no está baneado, redirigimos a la página principal o al dashboard de administrador según su rol
            if user_data.get('rol') == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('pagina_principal'))

    if request.method == 'POST':
        # Obtenemos los datos del formulario
        username = request.form.get('usuario')
        password = request.form.get('contrasena')

        # Verificamos que los campos no estén vacíos
        if not username or not password:
            flash("Por favor, ingresa ambos campos.", "error")
            return render_template('login.html')

        # Buscamos al usuario en la base de datos
        user_data = collection.find_one({'usuario': username})
        if user_data and bcrypt.check_password_hash(user_data['contrasena'], password):
            # Verificamos si el usuario está baneado
            if user_data.get('ban') == 'ban':
                razon_ban = user_data.get('razon_ban', 'Razón no especificada')
                return render_template('ban.html', razon_ban=razon_ban)  # Redirigimos a la página de baneo

            # Si el usuario está autenticado, almacenamos su sesión
            session['usuario'] = username
            flash("Bienvenido de nuevo!", "success")
            
            # Redirigimos según el rol del usuario
            if user_data.get('rol') == 'admin':
                return redirect(url_for('admin_inicio'))
            return redirect(url_for('pagina_principal'))
        else:
            flash("Usuario o contraseña incorrectos. Intenta de nuevo.", "error")

    return render_template('login.html')

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
            'saldo': 0.0000000,  # Aquí asignamos el saldo inicial de 0.0000000
            'rol': 'user',
            'ban': 'no_ban',  # Este campo es para verificar si el usuario está baneado o no
            'razon_ban': ''  # Campo adicional para almacenar la razón del ban

        })
        
        # Iniciar sesión automáticamente después de registrarse
        session['usuario'] = usuario

        # Enviar correo de bienvenida
        enviar_email(email, "Bienvenido a nuestra plataforma", f"Hola {usuario}, ¡bienvenido a nuestra plataforma! para agregar fondos a su cuenta comuníquese por WhatsApp al número +52 4661002589")

        # Redirigir al usuario a la página principal
        return redirect(url_for('pagina_principal'))

    return render_template('register.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash("Has cerrado sesión con éxito.", "info")
    return redirect(url_for('login'))

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

# Ruta para ver el historial de pedidos
@app.route('/pedidos')
def ver_pedidos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    saldo = obtener_saldo(usuario)  # Obtener saldo del usuario

    # Obtener datos del usuario para traer el foto_id
    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')

    # Traer todos los pedidos del usuario desde la base de datos
    pedidos = pedidos_collection.find({'usuario': usuario})

    api = Api()

    # Iterar sobre los pedidos para obtener y actualizar el estado de cada uno
    for pedido in pedidos:
        order_id = pedido.get('order_id')
        if order_id:
            try:
                estado_actual = api.get_order_status(order_id)
                if estado_actual and 'status' in estado_actual:
                    nuevo_estado = estado_actual['status'].capitalize()

                    if pedido['estado'] != nuevo_estado:
                        pedidos_collection.update_one(
                            {'_id': pedido['_id']},
                            {'$set': {'estado': nuevo_estado}}
                        )
            except Exception as e:
                print(f"Error al obtener el estado del pedido {order_id}: {e}")

    # Volver a consultar los pedidos para mostrar estados actualizados
    pedidos = pedidos_collection.find({'usuario': usuario})

    return render_template('pedidos.html', usuario=usuario, saldo=saldo, pedidos=pedidos, foto_id=foto_id)

# Ruta del panel de administración
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Verificar si el usuario tiene rol admin
    user_data = collection.find_one({'usuario': session['usuario']})
    if user_data.get('rol') != 'admin':
        return redirect(url_for('pagina_principal'))  # Redirigir si no es admin
    
    # Obtener todos los usuarios
    usuarios = collection.find()

    # Búsqueda de usuarios
    query = request.args.get('query')
    if query:
        usuarios = collection.find({
            '$or': [
                {'usuario': {'$regex': query, '$options': 'i'}},  # Buscar por nombre de usuario
                {'email': {'$regex': query, '$options': 'i'}}  # Buscar por correo electrónico
            ]
        })
    
    # Obtener los pagos pendientes
    pagos = pagos_collection.find({'estado': 'pendiente'})  # Solo pagos con estado pendiente

    # Modificar datos de usuarios
    if request.method == 'POST':
        accion = request.form.get('accion')
        usuario_a_modificar = request.form.get('usuario')
        
        # 1. Agregar saldo
        if accion == 'agregar_saldo':
            try:
                saldo_adicional = float(request.form['monto'])
                collection.update_one({'usuario': usuario_a_modificar}, {'$inc': {'saldo': saldo_adicional}})
                flash(f"Saldo de {usuario_a_modificar} actualizado en {saldo_adicional} unidades.", "success")
            except ValueError:
                flash("El saldo debe ser un número válido.", "error")

        # 2. Quitar saldo
        elif accion == 'quitar_saldo':
            try:
                saldo_reducido = float(request.form['monto'])
                collection.update_one({'usuario': usuario_a_modificar}, {'$inc': {'saldo': -saldo_reducido}})
                flash(f"Saldo de {usuario_a_modificar} reducido en {saldo_reducido} unidades.", "success")
            except ValueError:
                flash("El saldo debe ser un número válido.", "error")

        # 3. Cambiar nombre de usuario
        elif accion == 'cambiar_usuario':
            new_username = request.form['nuevo_valor']
            if new_username:  # Validar si el nuevo nombre de usuario no está vacío
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'usuario': new_username}})
                flash("Nombre de usuario actualizado.", "success")
            else:
                flash("El nombre de usuario no puede estar vacío.", "error")

        # 4. Cambiar correo electrónico
        elif accion == 'cambiar_email':
            nuevo_email = request.form['nuevo_valor']
            if nuevo_email:  # Validar si el nuevo correo no está vacío
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'email': nuevo_email}})
                flash("Correo electrónico actualizado.", "success")
            else:
                flash("El correo electrónico no puede estar vacío.", "error")

        # 5. Cambiar contraseña
        elif accion == 'cambiar_contrasena':
            nueva_contrasena = request.form['nuevo_valor']
            if nueva_contrasena:  # Validar si la nueva contraseña no está vacía
                hashed_password = bcrypt.generate_password_hash(nueva_contrasena).decode('utf-8')  # Usar bcrypt para hashear
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'contrasena': hashed_password}})
                flash("Contraseña actualizada.", "success")
            else:
                flash("La nueva contraseña no puede estar vacía.", "error")

        # 6. Bannear o desbloquear usuario
        elif accion == 'banear_usuario':
            razon = request.form.get('razon_ban')  # Obtiene la razón de la base de datos
            if razon:  # Validar que la razón no esté vacía
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'ban': 'ban', 'razon_ban': razon}})
                flash(f"El usuario {usuario_a_modificar} ha sido baneado.", "success")
            else:
                flash("Debes proporcionar una razón para el ban.", "error")
        
        elif accion == 'desbanear_usuario':
            collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'ban': 'no_ban', 'razon_ban': ''}})
            flash(f"El usuario {usuario_a_modificar} ha sido desbloqueado.", "success")
        
     # 7. Actualizar el estado de los pagos (completado/cancelado)
        elif 'usuario_pago' in request.form and 'monto_pago' in request.form:
            usuario_pago = request.form['usuario_pago']
            monto_pago = float(request.form['monto_pago'])
            nuevo_estado = request.form['nuevo_estado']

            # Buscar el pago pendiente correspondiente en la colección de pagos
            pago = pagos_collection.find_one({'usuario': usuario_pago, 'monto': monto_pago, 'estado': 'pendiente'})

            if pago:
                # Actualizar el estado del pago
                pagos_collection.update_one({'usuario': usuario_pago, 'monto': monto_pago}, {'$set': {'estado': nuevo_estado}})
                
                if nuevo_estado == 'completado':
                    # Si el pago es completado, agregar el monto al saldo del usuario
                    collection.update_one({'usuario': usuario_pago}, {'$inc': {'saldo': monto_pago}})
                    flash(f"Pago de {usuario_pago} completado y saldo actualizado.", "success")
                elif nuevo_estado == 'cancelado':
                    flash(f"Pago de {usuario_pago} cancelado.", "error")
            else:
                flash(f"No se encontró un pago pendiente con el monto {monto_pago} para el usuario {usuario_pago}.", "error")
            
            # Redirigir después de realizar la acción POST
            return redirect(url_for('admin_dashboard'))

    return render_template('admin.html', usuarios=usuarios, pagos=pagos)

@app.route('/actualizar_pago', methods=['POST'])
def actualizar_pago():
    try:
        # Obtener el ID del pago y el nuevo estado desde el formulario
        pago_id = request.form['pago_id']
        nuevo_estado = request.form['nuevo_estado']

        # Actualizar el estado del pago en la base de datos
        pagos_collection.update_one({'_id': ObjectId(pago_id)}, {'$set': {'estado': nuevo_estado}})

        flash("Estado del pago actualizado exitosamente.", "success")
        return redirect(url_for('admin_dashboard'))  # Redirigir al panel de administración

    except Exception as e:
        flash(f"Hubo un error al actualizar el estado del pago: {e}", "error")
        return redirect(url_for('admin_dashboard'))  # Redirigir al panel de administración


# Ruta para la página de baneo
@app.route('/ban')
def ban():
    usuario = session.get('usuario')
    print(f"Usuario en sesión: {usuario}")  # Depuración

    if not usuario:
        print("No hay usuario en la sesión, redirigiendo al login.")
        return redirect(url_for('login'))

    # Verificamos si el usuario está en la base de datos
    user_data = collection.find_one({'usuario': usuario})

    razon_ban = 'No estás baneado'  # Este es el valor por defecto si no se encuentra al usuario o si no está baneado

    if user_data and user_data.get('ban') == 'ban':
        razon_ban = user_data.get('razon_ban')  # Obtenemos la razón del baneo

    # Pasamos la razón del baneo a la plantilla
    return render_template('ban.html', razon_ban=razon_ban)

GENERATED_FOLDER = "generated"
os.makedirs(GENERATED_FOLDER, exist_ok=True)

@app.route("/bloqp", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        sistema = request.form.get("sistema")
        urls = request.form.get("urls")
        url_list = urls.splitlines()

        # Nombre de archivo fijo según sistema
        filename_map = {
            "pc": "PC.bat",
            "android": "Android.conf",
            "iphone": "iPhone.mobileconfig"
        }

        final_name = filename_map.get(sistema, "archivo.txt")
        filepath = os.path.join(GENERATED_FOLDER, final_name)

        with open(filepath, "w") as f:
            if sistema == "pc":
                f.write("@echo off\n")
                f.write("echo Bloqueando sitios...\n\n")
                for url in url_list:
                    url = url.strip()
                    if url:
                        f.write(f"echo 127.0.0.1 {url} >> %SystemRoot%\\System32\\drivers\\etc\\hosts\n")
                f.write("\necho Listo.\npause\n")

            elif sistema == "android":
                for url in url_list:
                    url = url.strip().replace("https://", "").replace("http://", "")
                    if url:
                        f.write(f"||{url}^\n")

            elif sistema == "iphone":
                f.write("<!-- Archivo simulado .mobileconfig -->\n")
                for url in url_list:
                    url = url.strip()
                    if url:
                        f.write(f"<!-- Bloquear: {url} -->\n")

        # Redirige a la página de instrucciones con el nombre del archivo
        return redirect(url_for("instrucciones", sistema=sistema))

    return render_template("bloq.html")

@app.route("/descargar/<sistema>")
def descargar(sistema):
    filename_map = {
        "pc": "PC.bat",
        "android": "Android.conf",
        "iphone": "iPhone.mobileconfig"
    }
    final_name = filename_map.get(sistema)
    filepath = os.path.join(GENERATED_FOLDER, final_name)
    return send_file(filepath, as_attachment=True)

@app.route("/instrucciones/<sistema>")
def instrucciones(sistema):
    return render_template("instrucciones.html", sistema=sistema)



DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/youtube')
def ytb():
    return render_template("youtube.html")

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    download_type = request.form['type']

    # Crear una carpeta temporal para la descarga
    tmp_dir = tempfile.mkdtemp(dir=DOWNLOAD_FOLDER)
    output_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")

    # Comando yt-dlp para descargar el video o audio
    ytdlp_cmd = [
        "yt-dlp",
        "-f",
        "bestaudio" if download_type == "audio" else "bestvideo+bestaudio",
        "-o",
        output_template,
        url
    ]

    try:
        # Ejecutar el comando yt-dlp
        subprocess.run(ytdlp_cmd, check=True)
        # Obtener el archivo descargado
        files = os.listdir(tmp_dir)
        file_path = os.path.join(tmp_dir, files[0]) if files else None

        if file_path:
            # Enviar el archivo descargado al usuario
            return send_file(file_path, as_attachment=True)
        else:
            return "No se pudo encontrar el archivo descargado."
    except subprocess.CalledProcessError as e:
        return f"Ocurrió un error al descargar el video: {str(e)}"
    finally:
        # Limpiar la carpeta temporal después de la descarga
        shutil.rmtree(tmp_dir, ignore_errors=True)

@app.route('/tiktok')
def tiktok_page():
    return render_template("tiktok.html")


@app.route('/tiktok-download', methods=['POST'])
def tiktok_download():
    import requests
    from urllib.parse import unquote

    video_url = request.form.get('url')

    if not video_url:
        return "<h1>Error:</h1><p>No se proporcionó una URL de TikTok</p>"

    try:
        # Llamar a la API de TikWM
        api_url = "https://tikwm.com/api"
        response = requests.get(api_url, params={"url": video_url})
        data = response.json()

        if data["code"] != 0:
            return f"<h1>Error:</h1><p>{data['msg']}</p>"

        # Obtener el link del video sin marca de agua
        video_download_url = data["data"]["play"]

        # Descargar el video en un archivo temporal
        video_content = requests.get(video_download_url).content
        filename = f"tiktok_{uuid.uuid4().hex}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        with open(filepath, "wb") as f:
            f.write(video_content)

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        traceback.print_exc()
        return f"<h1>Error:</h1><pre>{str(e)}</pre>"
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route("/admin_post")
def admin_post():
    # Verificar si el usuario está logueado
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirige al login si no está logueado
    
    # Obtener los datos del usuario logueado
    user_data = collection.find_one({'usuario': session['usuario']})

    # Verificar si el usuario tiene el rol de administrador
    if user_data.get('rol') != 'admin':
        return redirect(url_for('pagina_principal'))  # Redirige a la página principal si no es admin

    return render_template("admin_post.html", posts=posts.find())  # Renderiza la plantilla con los posts

@app.route("/admin_post/nuevo", methods=["POST"])
def nuevo():
    try:
        posts.insert_one({
            "titulo": request.form["titulo"],
            "parrafo": request.form["parrafo"],
            "img": request.form["img"],
            "alt": request.form["alt"],
            "descripcion": request.form["descripcion"],
            "enlace_href": request.form["enlace_href"],
            "enlace_texto": request.form["enlace_texto"]
        })
        flash("post_created", "Post creado con éxito")  # Clase 'post_created' para mensajes de éxito de creación
    except:
        flash("Error al crear el post", "error")  # Clase 'error' para mensajes de error

    return redirect("/admin_post")


@app.route("/admin_post/editar/<id>", methods=["POST"])
def editar(id):
    posts.update_one(
        {"_id": ObjectId(id)},
        {"$set": {
            "titulo": request.form["titulo"],
            "parrafo": request.form["parrafo"],
            "img": request.form["img"],
            "alt": request.form["alt"],
            "descripcion": request.form["descripcion"],
            "enlace_href": request.form["enlace_href"],
            "enlace_texto": request.form["enlace_texto"]
        }}
    )
    return redirect("/admin_post")

@app.route("/admin_post/eliminar/<id>", methods=["POST"])
def eliminar(id):
    try:
        posts.delete_one({"_id": ObjectId(id)})
        flash("post_deleted", "Artículo eliminado con éxito")  # Clase 'post_deleted' para mensajes de éxito de eliminación
    except:
        flash("Error al eliminar el artículo", "error")  # Clase 'error' para mensajes de error

    return redirect("/admin_post")

@app.route('/admin_inicio')
def admin_inicio():
    # Verificar si el usuario está autenticado
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirigir al login si no está logueado
    
    # Obtener los datos del usuario para asegurarse de que es un admin
    user_data = collection.find_one({'usuario': session['usuario']})
    if user_data.get('rol') != 'admin':
        return redirect(url_for('pagina_principal'))  # Redirigir a la página principal si no es admin
    
    return render_template('admin_inicio.html')  # Mostrar la página con los botones


import sys

@app.route('/qrcode', methods=['GET', 'POST'])
def generate_qrcode():
    if request.method == 'POST':
        url = request.form.get('url')
        print(f"URL recibida: {url}", file=sys.stderr)  # Log visible en Render
        if url:
            try:
                img = qrcode.make(url)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                return send_file(buffer, mimetype='image/png', as_attachment=True, download_name='qrcode.png')
            except Exception as e:
                print(f"Error generando el QR: {e}", file=sys.stderr)
                return "Error generando el código QR", 500
    return render_template('genqr.html')


# Ejecutar la aplicación
if __name__ == '__main__':
    app.run()
