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
from bson.decimal128 import Decimal128
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import jsonify
from bson.json_util import dumps
from datetime import datetime, timedelta


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
pedidos_streaming = db['streaming']
soporte_collection = db['soporteMensajes']
freefire_collection = db['diamantes']

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
    saldo = obtener_saldo(usuario)

    if request.method == 'POST':
         
         if 'change-whatsapp' in request.form:
            new_whatsapp = request.form['new-whatsapp'].strip()
            if new_whatsapp:
                collection.update_one({'usuario': usuario}, {'$set': {'whatsapp': new_whatsapp}})
                flash("Número de WhatsApp actualizado con éxito.", "success")
            else:
                flash("El número de WhatsApp no puede estar vacío.", "error")
            return redirect(url_for('mi_perfil'))


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

    return render_template('mi_perfil.html',whatsapp=user_data.get('whatsapp', ''), usuario=user_data['usuario'], email=user_data['email'], foto_id=foto_id,saldo=saldo)

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

    user_data = collection.find_one({'usuario': session['usuario']})
    if not user_data:
        session.clear()
        return redirect(url_for('login'))

    if user_data.get('ban') == 'ban':
        razon_ban = user_data.get('razon_ban', 'Razón no especificada')
        return render_template('ban.html', razon_ban=razon_ban)

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

    categories = [c for c in categories if c is not None and isinstance(c, dict)]
    services = [s for s in services if s is not None and isinstance(s, dict)]

    foto_id = user_data.get('foto_id')
    mi_codigo = user_data.get('codigo_referido')
    enlace_referido = user_data.get('enlace_referido')

    # Buscar todos los usuarios referidos por mí
    referidos = []
    if mi_codigo:
        cursor = collection.find({'referido_por': mi_codigo})
        for doc in cursor:
            fecha_registro = doc.get('fecha_registro')
            tiempo_transcurrido = ""
            if fecha_registro:
                ahora = datetime.utcnow()
                diferencia = relativedelta(ahora, fecha_registro)
                if diferencia.years > 0:
                    tiempo_transcurrido = f"{diferencia.years} years ago"
                elif diferencia.months > 0:
                    tiempo_transcurrido = f"{diferencia.months} months ago"
                elif diferencia.days > 0:
                    tiempo_transcurrido = f"{diferencia.days} days ago"
                else:
                    tiempo_transcurrido = "Just now"

            referidos.append({
    'usuario': doc.get('usuario'),
    'nombre': doc.get('nombre'),
    'tiempo': tiempo_transcurrido,
    'foto_id': doc.get('foto_id')  # <-- agregar esto
})


    return render_template(
        'index.html',
        usuario=session['usuario'],
        saldo=saldo,
        categories=categories,
        services=services,
        foto_id=foto_id,
        codigo_referido=mi_codigo,
        enlace_referido=enlace_referido,
        referidos=referidos
    )


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
                'fecha_creacion': datetime.datetime.now()
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
        data = request.get_json()

        usuario = data['usuario']
        monto = float(data['monto'])  # asegura que sea numérico
        metodo_pago = data['metodo_pago']
        estado = data.get('estado', 'pendiente')
        fecha = datetime.now()

        resultado = pagos_collection.insert_one({
            'usuario': usuario,
            'monto': monto,
            'metodo_pago': metodo_pago,
            'estado': estado,
            'fecha_creacion': fecha
        })

        return jsonify({'success': True, 'message': 'Pago guardado exitosamente.'})

    except Exception as e:

        return jsonify({'success': False, 'error': str(e)})

    
    

@app.route('/movimientos')
def movimientos():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirigir a login si no hay usuario en la sesión
    
    # Obtener el usuario desde la sesión
    usuario = session['usuario']

    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = obtener_saldo(usuario)

    # Obtener los movimientos de pagos del usuario desde la base de datos
    movimientos_usuario = pagos_collection.find({'usuario': usuario})

    pagos = []
    for pago in movimientos_usuario:
        estado = pago.get('estado', 'pendiente')

       
        monto = pago.get('monto', 0)
        if isinstance(monto, (int, float)):
            monto_redondeado = round(monto, 2)
        else:  
            try:
                monto_redondeado = round(float(monto), 2)
            except ValueError:
                monto_redondeado = 0  

        pagos.append({
            'descripcion': pago.get('metodo_pago', 'Desconocido'),
            'monto': monto_redondeado,
            'estado': estado,
            'fecha': pago.get('fecha', datetime.now()).strftime('%Y-%m-%d')
        })
    
    return render_template('mov.html', usuario=usuario, pagos=pagos, foto_id=foto_id, saldo=saldo)



# Ruta para agregar una orden
@app.route('/agregar_orden', methods=['GET', 'POST'])
def agregar_orden():
    # Verificar si el usuario está autenticado
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirige a la página de login si no está autenticado

    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
    saldo = obtener_saldo(usuario)  # Obtener saldo del usuario
    foto_id = user_data.get('foto_id')

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
                        flash(f"Hubo un problema al crear el pedido", "error")
                except Exception as e:
                    flash("Error al realizar el pedido. Intenta más tarde.", "error")
            else:
                flash("No tienes suficiente saldo para realizar esta orden.", "error")

        # Redirigir después de procesar el formulario (PRG)
        return redirect(url_for('agregar_orden'))

    # Si es un GET, simplemente renderizar la página con las categorías y servicios
    return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services, foto_id=foto_id)

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
            session.permanent = 'remember' in request.form
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
    referral_code = request.args.get('ref')  # Leer desde URL por si viene con ?ref=...

    if request.method == 'POST':
        nombre_completo = request.form.get('name')
        username = request.form.get('username')
        whatsapp_country = request.form.get('whatsapp_country')
        whatsapp_number = request.form.get('whatsapp_number')
        email = request.form.get('email')
        referral_code_form = request.form.get('referral_code')  # Leer desde el formulario

        # Usar el código de referido de la URL si no se proporcionó en el formulario
        # o si el de la URL es el original que se debe mantener
        final_referral_code_input = referral_code if referral_code else referral_code_form

        if request.form.get('password') != request.form.get('password_confirmation'):
            flash("Las contraseñas no coinciden.")
            return redirect(url_for('registro', ref=final_referral_code_input))

        if collection.find_one({'email': email}):
            flash("El correo electrónico ya está registrado.")
            return redirect(url_for('registro', ref=final_referral_code_input))

        if collection.find_one({'usuario': username}):
            flash("El nombre de usuario ya está en uso.")
            return redirect(url_for('registro', ref=final_referral_code_input))

        # Si hay código de referido, validar que exista en la base de datos
        if final_referral_code_input:
            referido_existente = collection.find_one({'codigo_referido': final_referral_code_input})
            if not referido_existente:
                flash("El código de referido no es válido.")
                return redirect(url_for('registro'))

        whatsapp = f"+{whatsapp_country}{whatsapp_number}"
        hashed_password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        
        # --- Lógica para generar y verificar la unicidad del código de referido ---
        base_codigo_referido = username
        counter = 1
        codigo_referido_generado = f"{base_codigo_referido}_{counter}"
        
        # Bucle para asegurar que el código de referido sea único
        while collection.find_one({'codigo_referido': codigo_referido_generado}):
            counter += 1
            codigo_referido_generado = f"{base_codigo_referido}_{counter}"
        # --- Fin de la lógica de unicidad ---

        nuevo_usuario = {
            'nombre': nombre_completo,
            'usuario': username,
            'whatsapp': whatsapp,
            'email': email,
            'contrasena': hashed_password,
            'saldo': 0.0000000,
            'rol': 'user',
            'ban': 'no_ban',
            'razon_ban': '',
            'fecha_registro': datetime.utcnow(),
            'referido_por': final_referral_code_input if final_referral_code_input else None,
            'codigo_referido': codigo_referido_generado, # Usar el código único generado
            'enlace_referido': f"https://kingshop7.onrender.com/registro?ref={codigo_referido_generado}" # Usar el código único generado
        }

        collection.insert_one(nuevo_usuario)
        session['usuario'] = username

        enviar_email(
            email,
            "Bienvenido a nuestra plataforma",
            f"Hola {nombre_completo}, ¡bienvenido a nuestra plataforma! Para agregar fondos a tu cuenta, comunícate por WhatsApp al número +52 4661002589"
        )

        return redirect(url_for('pagina_principal'))

    # Mostrar formulario con código prellenado si viene de ?ref=
    return render_template('register.html', referral_code=referral_code)


# Ruta para cerrar sesión
@app.route('/logout', methods=['GET', 'POST'])
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
    
    user_data = collection.find_one({'usuario': session['usuario']})
    if user_data.get('rol') != 'admin':
        return redirect(url_for('pagina_principal'))
    
    # Llama a la función para eliminar pagos pendientes expirados
    delete_expired_payments()

    # Obtener todos los usuarios y convertir Decimal128 a float
    usuarios_cursor = collection.find()
    usuarios_list = []
    for user in usuarios_cursor:
        if 'saldo' in user and isinstance(user['saldo'], Decimal128):
            user['saldo'] = float(str(user['saldo'])) # Convertir Decimal128 a string y luego a float
        usuarios_list.append(user)

    query = request.args.get('query')
    if query:
        # Si hay una consulta, filtrar la lista de usuarios ya convertida
        filtered_users = []
        for user in usuarios_list:
            if (query.lower() in user.get('usuario', '').lower() or
                query.lower() in user.get('email', '').lower()):
                filtered_users.append(user)
        usuarios_list = filtered_users
    
    # Obtener los pagos pendientes y convertir Decimal128 a float
    pagos_cursor = pagos_collection.find({'estado': 'pendiente'})
    pagos_list = []
    for pago in pagos_cursor:
        if 'monto' in pago and isinstance(pago['monto'], Decimal128):
            pago['monto'] = float(str(pago['monto'])) # Convertir Decimal128 a string y luego a float
        pagos_list.append(pago)

    if request.method == 'POST':
        accion = request.form.get('accion')
        usuario_a_modificar = request.form.get('usuario')
        
        if accion == 'agregar_saldo':
            try:
                # Asegurarse de que el monto se convierta correctamente a float
                saldo_adicional = float(request.form['monto'])
                collection.update_one({'usuario': usuario_a_modificar}, {'$inc': {'saldo': saldo_adicional}})
                flash(f"Saldo de {usuario_a_modificar} actualizado en {saldo_adicional} unidades.", "success")
            except ValueError:
                flash("El saldo debe ser un número válido.", "error")

        elif accion == 'quitar_saldo':
            try:
                # Asegurarse de que el monto se convierta correctamente a float
                saldo_reducido = float(request.form['monto'])
                collection.update_one({'usuario': usuario_a_modificar}, {'$inc': {'saldo': -saldo_reducido}})
                flash(f"Saldo de {usuario_a_modificar} reducido en {saldo_reducido} unidades.", "success")
            except ValueError:
                flash("El saldo debe ser un número válido.", "error")

        elif accion == 'cambiar_usuario':
            new_username = request.form['nuevo_valor']
            if new_username:
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'usuario': new_username}})
                flash("Nombre de usuario actualizado.", "success")
            else:
                flash("El nombre de usuario no puede estar vacío.", "error")

        elif accion == 'cambiar_email':
            nuevo_email = request.form['nuevo_valor']
            if nuevo_email:
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'email': nuevo_email}})
                flash("Correo electrónico actualizado.", "success")
            else:
                flash("El correo electrónico no puede estar vacío.", "error")

        elif accion == 'cambiar_contrasena':
            nueva_contrasena = request.form['nuevo_valor']
            if nueva_contrasena:
                hashed_password = bcrypt.generate_password_hash(nueva_contrasena).decode('utf-8')
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'contrasena': hashed_password}})
                flash("Contraseña actualizada.", "success")
            else:
                flash("La nueva contraseña no puede estar vacía.", "error")

        elif accion == 'banear_usuario':
            razon = request.form.get('razon_ban')
            if razon:
                collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'ban': 'ban', 'razon_ban': razon}})
                flash(f"El usuario {usuario_a_modificar} ha sido baneado.", "success")
            else:
                flash("Debes proporcionar una razón para el ban.", "error")
        
        elif accion == 'desbanear_usuario':
            collection.update_one({'usuario': usuario_a_modificar}, {'$set': {'ban': 'no_ban', 'razon_ban': ''}})
            flash(f"El usuario {usuario_a_modificar} ha sido desbloqueado.", "success")
        
        elif 'usuario_pago' in request.form and 'monto_pago' in request.form:
            usuario_pago = request.form['usuario_pago']
            monto_pago = float(request.form['monto_pago'])
            nuevo_estado = request.form['nuevo_estado']

            # Asegurarse de comparar con Decimal128 si así está en la base de datos
            pago = pagos_collection.find_one({'usuario': usuario_pago, 'monto': Decimal128(str(monto_pago)), 'estado': 'pendiente'})

            if pago:
                pagos_collection.update_one({'usuario': usuario_pago, 'monto': Decimal128(str(monto_pago))}, {'$set': {'estado': nuevo_estado}})
                
                if nuevo_estado == 'completado':
                    collection.update_one({'usuario': usuario_pago}, {'$inc': {'saldo': monto_pago}})
                    flash(f"Pago de {usuario_pago} completado y saldo actualizado.", "success")
                elif nuevo_estado == 'cancelado':
                    flash(f"Pago de {usuario_pago} cancelado.", "error")
            else:
                flash(f"No se encontró un pago pendiente con el monto {monto_pago} para el usuario {usuario_pago}.", "error")
            
            return redirect(url_for('admin_dashboard'))

    return render_template('admin.html', usuarios=usuarios_list, pagos=pagos_list)

def delete_expired_payments():
    # Define el umbral de tiempo (24 horas atrás desde ahora)
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    
    # Busca pagos pendientes cuya fecha de creación sea anterior al umbral
    expired_payments = pagos_collection.find({
        'estado': 'pendiente',
        'fecha_creacion': {'$lt': time_threshold}
    })
    
    deleted_count = 0
    for payment in expired_payments:
        pagos_collection.delete_one({'_id': payment['_id']})
        deleted_count += 1
    
    if deleted_count > 0:
        flash(f"Se eliminaron {deleted_count} pagos pendientes expirados.")


@app.route('/actualizar_pago', methods=['POST'])
def actualizar_pago():
    try:
        pago_id = request.form['pago_id']
        nuevo_estado = request.form['nuevo_estado']

        # Obtener el pago antes de actualizar para verificar el monto y el usuario
        pago = pagos_collection.find_one({'_id': ObjectId(pago_id)})

        if pago:
            pagos_collection.update_one({'_id': ObjectId(pago_id)}, {'$set': {'estado': nuevo_estado}})

            if nuevo_estado == 'completado':
                # Si el pago es completado, agregar el monto al saldo del usuario
                usuario_pago = pago.get('usuario')
                monto_pago = pago.get('monto')
                # Convertir monto_pago a float si es Decimal128 antes de sumarlo
                if isinstance(monto_pago, Decimal128):
                    monto_pago = float(str(monto_pago))

                if usuario_pago and monto_pago is not None:
                    collection.update_one({'usuario': usuario_pago}, {'$inc': {'saldo': monto_pago}})
                    flash(f"Pago de {usuario_pago} completado y saldo actualizado.", "success")
                else:
                    flash("No se pudo obtener la información del usuario o monto del pago.", "error")
            elif nuevo_estado == 'cancelado':
                flash("Estado del pago actualizado a cancelado.", "success")
            else:
                flash("Estado del pago actualizado exitosamente.", "success")
        else:
            flash("Pago no encontrado.", "error")

        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        flash(f"Hubo un error al actualizar el estado del pago: {e}", "error")
        return redirect(url_for('admin_dashboard'))

@app.route('/ban')
def ban():
    usuario = session.get('usuario')
    print(f"Usuario en sesión: {usuario}")

    if not usuario:
        print("No hay usuario en la sesión, redirigiendo al login.")
        return redirect(url_for('login'))

    user_data = collection.find_one({'usuario': usuario})

    razon_ban = 'No estás baneado'

    if user_data and user_data.get('ban') == 'ban':
        razon_ban = user_data.get('razon_ban')

    return render_template('ban.html', razon_ban=razon_ban)


DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)



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
    

@app.route('/streaming', methods=['GET', 'POST'])
def streaming():
    if 'usuario' in session:
        user_data = collection.find_one({'usuario': session['usuario']})
        foto_id = user_data.get('foto_id')

        if user_data:
            if user_data.get('ban') == 'ban':
                return render_template('ban.html', razon_ban=user_data.get('razon_ban', 'Sin razón'))
            # Usuario logueado y no baneado
            return render_template('streaming.html', logueado=True, usuario=user_data['usuario'], saldo=user_data.get('saldo', 0),foto_id=foto_id)
        else:
            # No encontró datos del usuario en BD (por si la sesión está corrupta)
            session.pop('usuario', None)
            return render_template('streaming.html', logueado=False)
    else:
        # No hay usuario en sesión
        return render_template('streaming.html', logueado=False)



@app.route('/comprar', methods=['POST'])
def comprar():
    if 'usuario' not in session:
        return jsonify({'message': 'Debes iniciar sesión'}), 401

    try:
        data = request.get_json()

        servicio = data.get('servicio')
        precio = Decimal(data.get('precio'))
        nombre = data.get('nombre')
        whatsapp = data.get('whatsapp')
        email = data.get('email', '')
        observaciones = data.get('observaciones', '')

        user_data = collection.find_one({'usuario': session['usuario']})
        saldo_decimal128 = user_data.get('saldo', Decimal128('0'))

        # Convertimos saldo
        if isinstance(saldo_decimal128, Decimal128):
            saldo_actual = saldo_decimal128.to_decimal()
        else:
            saldo_actual = Decimal(str(saldo_decimal128))

        if saldo_actual >= precio:
            nuevo_saldo = saldo_actual - precio

            # Actualizar saldo
            collection.update_one(
                {'usuario': session['usuario']},
                {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
            )

            # Guardar el pedido
            pedidos_streaming.insert_one({
                'usuario': session['usuario'],
                'servicio': servicio,
                'precio': float(precio),
                'nombre': nombre,
                'whatsapp': whatsapp,
                'email': email,
                'observaciones': observaciones
            })

            return jsonify({'message': f'Has comprado {servicio} correctamente. En menos de 24 horas te enviaremos los detalles por whatsapp Tu nuevo saldo es ${nuevo_saldo:.2f}'}), 200
        else:
            return jsonify({'message': 'Saldo insuficiente'}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Error interno del servidor'}), 500
    
@app.route("/imgcode")
def imgcode():
    return render_template('gencode.html')

@app.route("/ajedrez")
def ajedrez():
    return render_template('ajedres.html')

@app.route("/principal")
def smmprincipal():
    return render_template('principal.html')

@app.route("/terminos")
def terminos():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirigir a login si no hay usuario en la sesión
    
    # Obtener el usuario desde la sesión
    usuario = session['usuario']

    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = obtener_saldo(usuario)
    return render_template('terminos.html',usuario=session['usuario'],
        saldo=saldo,
        foto_id=foto_id)

@app.route('/pedidosStreaming')
def ver_pedidos_streaming():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # o maneja según tu flujo

    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = obtener_saldo(usuario)
    # Obtener los pedidos del usuario desde la colección pedidos_streaming
    pedidos = list(pedidos_streaming.find({'usuario': usuario}).sort('_id', -1))  # orden descendente por fecha

    return render_template('Streamingpedidos.html', pedidos=pedidos,usuario=session['usuario'],saldo=saldo,foto_id=foto_id)


@app.route('/soporte', methods=['GET', 'POST'])
def soporte():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = obtener_saldo(usuario)

    if request.method == 'POST':
        asunto = request.form.get('asunto')
        mensaje = request.form.get('mensaje')

        # Puedes guardar esto en MongoDB si quieres:
        soporte_collection.insert_one({
            'usuario': session['usuario'],
            'asunto': asunto,
            'mensaje': mensaje,
            'fecha': datetime.now()
        })

        return render_template('soporte.html', mensaje="Tu mensaje ha sido enviado. Te responderemos pronto.")

    return render_template('soporte.html',usuario=session['usuario'],saldo=saldo,foto_id=foto_id)


@app.route('/admin_soporte')
def admin_soporte():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # Verificar si el usuario es admin
    user_data = collection.find_one({'usuario': session['usuario']})
    if not user_data or user_data.get('rol') != 'admin':
        return redirect(url_for('pagina_principal'))

    # Obtener mensajes de soporte
    mensajes = list(soporte_collection.find().sort('fecha', -1))  # más recientes primero

    return render_template('admin_soporte.html', mensajes=mensajes)


from bson import ObjectId

@app.route('/admin_streaming')
def admin_streaming():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    user_data = collection.find_one({'usuario': session['usuario']})
    if not user_data or user_data.get('rol') != 'admin':
        return redirect(url_for('pagina_principal'))

    # Filtro opcional desde query string
    estado = request.args.get('estado')  # "pendiente", "entregado" o None
    filtro = {}
    if estado in ('pendiente', 'entregado'):
        filtro['estado'] = estado

    pedidos = [
    {**p, '_id': str(p['_id'])}
    for p in pedidos_streaming.find(filtro).sort('_id', -1)
]

    return render_template('admin_streaming.html', pedidos=pedidos, filtro_estado=estado or '')


@app.route('/marcar_entregado/<pedido_id>', methods=['POST'])
def marcar_entregado(pedido_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    user_data = collection.find_one({'usuario': session['usuario']})
    if not user_data or user_data.get('rol') != 'admin':
        return redirect(url_for('pagina_principal'))

    pedidos_streaming.update_one(
        {'_id': ObjectId(pedido_id)},
        {'$set': {'estado': 'entregado'}}
    )
    return redirect(url_for('admin_streaming'))

@app.route('/diamantes')
def diamantes():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    user_data = collection.find_one({'usuario': session['usuario']})
    saldo = user_data.get('saldo', Decimal128('0')) # Asumimos que el saldo en DB es Decimal128
    foto_id = user_data.get('foto_id')

    if isinstance(saldo, Decimal128):
        saldo = saldo.to_decimal() # Convertir a Decimal para operaciones

    return render_template('diamantes.html', logueado=True, usuario=user_data['usuario'], saldo=saldo,
        foto_id=foto_id)


@app.route('/free-fire-diamonds', methods=['POST'])
def guardar_diamantes():
    if 'usuario' not in session:
        return jsonify({'success': False, 'redirect': url_for('login')}), 401

    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

    try:
        # Datos del pedido
        nombre = data.get("nombre")
        whatsapp = data.get("whatsapp")
        nick = data.get("nick")
        id_juego = data.get("idJuego")
        paquete = data.get("paquete")
        usuario_frontend = data.get("usuario")

        if usuario_frontend and usuario_frontend != session['usuario']:
            return jsonify({'success': False, 'error': 'Conflicto de usuario. Intenta de nuevo.'}), 403

        # Precios en USD ($)
        precios = {
            "520 + 52 Diamantes Bonus": Decimal('4.87'),
            "620 + 62 Diamantes Bonus": Decimal('5.64'),
            "830 + 80 Diamantes Bonus": Decimal('7.95'),
            "1060 + 106 Diamantes Bonus": Decimal('9.74'),
            "2180 + 218 Diamantes Bonus": Decimal('18.46'),
            "4360 + 436 Diamantes Bonus": Decimal('37.18'),
            "5600 + 560 Diamantes Bonus": Decimal('46.15'),
            "Tarjeta Semanal": Decimal('1.9'), # ¡Ajustado a USD!
            "Tarjeta Mensual": Decimal('9.25') # ¡Ajustado a USD! (asumiendo un precio similar semanal/mensual)
        }

        precio = precios.get(paquete)
        if precio is None:
            return jsonify({'success': False, 'error': 'Paquete no válido'}), 400

        user = collection.find_one({'usuario': session['usuario']})
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no encontrado en la base de datos.'}), 404

        saldo_actual = user.get('saldo', Decimal128('0'))

        if isinstance(saldo_actual, Decimal128):
            saldo_actual = saldo_actual.to_decimal()

        if saldo_actual < precio: # Comparar Decimal con Decimal
            return jsonify({'success': False, 'error': 'Saldo insuficiente'}), 400

        nuevo_saldo = saldo_actual - precio # Resta Decimal con Decimal
        collection.update_one(
            {'usuario': session['usuario']},
            {'$set': {'saldo': Decimal128(nuevo_saldo)}}
        )

        freefire_collection.insert_one({
            'usuario': session['usuario'],
            'nombre': nombre,
            'whatsapp': whatsapp,
            'nick': nick,
            'idJuego': id_juego,
            'paquete': paquete,
            'precio': float(precio), # Guardar como float si tu DB lo acepta, o Decimal128(precio) si MongoDB lo requiere como tal.
            'fecha': datetime.utcnow(),
            'estado': 'Pendiente' # <--- Asegura que el estado inicial sea 'Pendiente'

        })

        flash(f'✅ Compra realizada correctamente. Tu nuevo saldo es ${nuevo_saldo:.2f}', 'success')
        return jsonify({'success': True, 'redirect': url_for('diamantes')})

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash('❌ Error al procesar la compra.', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/historial-recargas')
def historial_recargas():
    # 1. Verificar si el usuario está logueado
    if 'usuario' not in session:
        flash('Por favor, inicia sesión para ver tu historial.', 'error')
        return redirect(url_for('login'))
    
    # Obtener el usuario desde la sesión
    usuario = session['usuario']

    user_data = collection.find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = obtener_saldo(usuario)

    try:
        # 2. Obtener el usuario actual de la sesión
        current_user = session['usuario']

        # 3. Consultar la colección freefire_collection para obtener las recargas de este usuario
        # Se ordenan por fecha de forma descendente para mostrar las más recientes primero
        recargas_cursor = freefire_collection.find({'usuario': current_user}).sort('fecha', -1)
        
        # Convertir el cursor a una lista para pasarla a la plantilla
        recargas = []
        for recarga in recargas_cursor:
            # Asegurarse de que el precio sea un float y la fecha esté formateada
            if isinstance(recarga.get('precio'), Decimal128):
                recarga['precio'] = recarga['precio'].to_decimal()
            elif isinstance(recarga.get('precio'), Decimal):
                recarga['precio'] = float(recarga['precio'])
            
            if isinstance(recarga.get('fecha'), datetime):
                recarga['fecha'] = recarga['fecha'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Asegurarse de que el estado exista, si no, poner un valor por defecto
            recarga['estado'] = recarga.get('estado', 'Pendiente')
            
            recargas.append(recarga)

        # 4. Renderizar la plantilla 'historial_recargas.html' y pasarle los datos
        return render_template('historial_recargas.html', logueado=True, usuario=current_user, recargas=recargas,
        saldo=saldo,
        foto_id=foto_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'❌ Error al cargar el historial de recargas: {str(e)}', 'error')
        return redirect(url_for('diamantes')) # O a una página de error, o al login


@app.route('/admin_diamantes')
def admin_diamantes():
    # 1. Verificar si el usuario ha iniciado sesión
    if 'usuario' not in session:
        flash('Por favor, inicia sesión para acceder al panel de administración.', 'error')
        return redirect(url_for('login'))

    # 2. Verificar si el usuario tiene rol de administrador
    user_data = collection.find_one({'usuario': session['usuario']})
    if not user_data or user_data.get('rol') != 'admin':
        flash('Acceso denegado. No tienes permisos de administrador.', 'error')
        return redirect(url_for('pagina_principal'))

    try:
        # 3. Filtrar pedidos por estado (opcional, desde query string)
        estado_filtro = request.args.get('estado')
        filtro_db = {}
        if estado_filtro:
            filtro_db['estado'] = estado_filtro.capitalize() 

        # 4. Obtener todos los pedidos de diamantes Free Fire
        pedidos_cursor = freefire_collection.find(filtro_db).sort('fecha', -1)
        
        # 5. Procesar los pedidos para la plantilla
        pedidos = []
        for pedido in pedidos_cursor:
            pedido['_id'] = str(pedido['_id'])
            
            if isinstance(pedido.get('precio'), Decimal128):
                pedido['precio'] = pedido['precio'].to_decimal()
            elif isinstance(pedido.get('precio'), Decimal):
                pedido['precio'] = float(pedido['precio'])
            
            if isinstance(pedido.get('fecha'), datetime):
                pedido['fecha'] = pedido['fecha'].strftime('%Y-%m-%d %H:%M:%S')
            
            pedido['estado'] = pedido.get('estado', 'Pendiente')
            
            pedidos.append(pedido)

        # 6. Renderizar la plantilla 'admin_diamantes.html' y pasarle los pedidos
        return render_template('admin_diamantes.html', 
                               logueado=True, 
                               usuario=session['usuario'], 
                               pedidos=pedidos,
                               filtro_estado=estado_filtro or '')

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'❌ Error al cargar el panel de administración de diamantes: {str(e)}', 'error')
        return redirect(url_for('pagina_principal'))

# --- RUTA PARA ACTUALIZAR EL ESTADO DE UN PEDIDO ---
@app.route('/admin/diamantes/update_status', methods=['POST'])
def update_diamantes_status():
    # --- DEBUG: Imprime el tipo de contenido de la petición ---
    print(f"DEBUG FLASK: Tipo de contenido recibido: {request.content_type}")
    # ---------------------------------------------------------

    # Verifica si el tipo de contenido es JSON
    if request.is_json:
        data = request.get_json()
        print(f"DEBUG FLASK: Datos recibidos por request.get_json(): {data}") # Debería imprimir el JSON
        order_id_str = data.get('order_id') # Espera 'order_id'
        new_status = data.get('status')     # Espera 'status'

        print(f"DEBUG FLASK: Extrayendo order_id: {order_id_str}, new_status: {new_status}")

        if not order_id_str or not new_status:
            print("DEBUG FLASK: ERROR: order_id o new_status están incompletos después de get().")
            return jsonify({'success': False, 'error': 'Datos incompletos.'}), 400

        try:
            # Intenta convertir el order_id a ObjectId solo si es necesario para MongoDB
            # Si tu _id en MongoDB es un string simple y no un ObjectId, omite esta línea.
            # Pero si es un ObjectId, es CRÍTICO convertirlo.
            order_id_obj = ObjectId(order_id_str)
        except Exception as e:
            print(f"DEBUG FLASK: Error al convertir order_id a ObjectId: {e}")
            return jsonify({'success': False, 'error': 'ID de pedido inválido.'}), 400

        # Realiza la actualización en MongoDB
        try:
            # Usa order_id_obj si convertiste a ObjectId, de lo contrario usa order_id_str
            result = freefire_collection.update_one(
                {'_id': order_id_obj}, # Usa order_id_obj aquí
                {'$set': {'estado': new_status}}
            )

            if result.matched_count > 0:
                flash(f'Pedido {order_id_str} actualizado a {new_status} correctamente.', 'success')
                return jsonify({'success': True, 'message': 'Estado actualizado.'}), 200
            else:
                flash(f'Pedido {order_id_str} no encontrado o no se pudo actualizar.', 'error')
                return jsonify({'success': False, 'error': 'Pedido no encontrado o sin cambios.'}), 404
        except Exception as e:
            print(f"DEBUG FLASK: Error al actualizar en la base de datos: {e}")
            flash('Error interno del servidor al actualizar el estado.', 'error')
            return jsonify({'success': False, 'error': 'Error interno del servidor.'}), 500
    else:
        print("DEBUG FLASK: Petición no es JSON o Content-Type incorrecto.")
        return jsonify({'success': False, 'error': 'Content-Type debe ser application/json.'}), 400
    

# --- RUTA PARA ELIMINAR UN PEDIDO ---
@app.route('/admin/diamantes/delete', methods=['POST'])
def delete_diamante_order():
    print(f"DEBUG: Petición recibida para eliminar orden.") # <-- Punto de depuración
    if 'usuario' not in session:
        return jsonify({'success': False, 'redirect': url_for('login')}), 401

    user_data = collection.find_one({'usuario': session['usuario']})
    if not user_data or user_data.get('rol') != 'admin':
        return jsonify({'success': False, 'error': 'Acceso denegado.'}), 403

    data = request.get_json()
    print(f"DEBUG: Datos recibidos por request.get_json(): {data}") # <-- Punto de depuración

    if not data:
        print("DEBUG: ERROR: Datos vacíos o nulos recibidos para eliminar.") # <-- Punto de depuración
        return jsonify({'success': False, 'error': 'Datos incompletos.'}), 400

    order_id = data.get('order_id')
    print(f"DEBUG: Extrayendo order_id para eliminar: {order_id}") # <-- Punto de depuración

    if not order_id:
        print("DEBUG: ERROR: order_id está incompleto para eliminar después de get().") # <-- Punto de depuración
        return jsonify({'success': False, 'error': 'ID de pedido no proporcionado.'}), 400

    try:
        result = freefire_collection.delete_one({'_id': ObjectId(order_id)})

        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': f'Pedido {order_id} eliminado correctamente.'})
        else:
            return jsonify({'success': False, 'error': f'Pedido {order_id} no encontrado.'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/transferir_saldo', methods=['GET', 'POST'])
def transferir_saldo():
    # Verificar si el usuario está autenticado
    if 'usuario' not in session:
        flash("Debes iniciar sesión para acceder a esta página.", "error")
        return redirect(url_for('login'))

    current_username = session['usuario']
    user_data = collection.find_one({'usuario': current_username})

    # Obtener saldo del emisor como decimal.Decimal para cálculos y display
    # Convertir Decimal128 a decimal.Decimal al leer de la DB
    if 'saldo' in user_data and isinstance(user_data['saldo'], Decimal128):
        current_sender_saldo = Decimal(str(user_data['saldo']))
    else:
        # Asegurarse de que el valor sea una cadena antes de convertirlo a Decimal
        current_sender_saldo = Decimal(str(user_data.get('saldo', '0'))) 

    # Obtener foto_id del usuario actual para pasar a la plantilla
    foto_id_current_user = str(user_data.get('foto_id')) if user_data.get('foto_id') else None

    # Lista para almacenar los usuarios encontrados por el buscador
    found_recipients = []
    search_query = request.args.get('search_query') # Obtener el término de búsqueda

    if search_query:
        # Buscar usuarios que coincidan con el término de búsqueda (ignorando mayúsculas/minúsculas)
        # Excluir al usuario actual de los resultados de búsqueda
        search_results_cursor = collection.find({
            '$and': [
                {'$or': [
                    {'usuario': {'$regex': search_query, '$options': 'i'}},
                    {'email': {'$regex': search_query, '$options': 'i'}}
                ]},
                {'usuario': {'$ne': current_username}} # Excluir al usuario actual
            ]
        })
        for user in search_results_cursor:
            found_recipients.append({
                'usuario': user.get('usuario'),
                'email': user.get('email'),
                'foto_id': str(user.get('foto_id')) if user.get('foto_id') else None # Incluir foto_id
            })

    if request.method == 'POST':
        recipient_username = request.form.get('recipient_username').strip()
        amount_str = request.form.get('amount').strip()

        try:
            # Convertir el monto de entrada a decimal.Decimal
            amount_to_transfer = Decimal(amount_str)
        except Exception: # Capturar una excepción más general para problemas de parseo
            flash("Monto inválido. Por favor, ingresa un número válido.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query)) # Mantener la búsqueda si falla

        if amount_to_transfer <= Decimal('0'): # Comparación con Decimal
            flash("El monto a transferir debe ser mayor que cero.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        # Comparación directa de decimal.Decimal
        if current_sender_saldo < amount_to_transfer:
            flash("Saldo insuficiente para realizar esta transferencia.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        if recipient_username == current_username:
            flash("No puedes transferir saldo a tu propia cuenta.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        recipient_data = collection.find_one({'usuario': recipient_username})

        if not recipient_data:
            flash(f"El usuario '{recipient_username}' no existe.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        try:
            # Obtener el saldo del receptor como decimal.Decimal
            if 'saldo' in recipient_data and isinstance(recipient_data['saldo'], Decimal128):
                recipient_current_saldo = Decimal(str(recipient_data['saldo']))
            else:
                recipient_current_saldo = Decimal(str(recipient_data.get('saldo', '0')))

            # Realizar cálculos con decimal.Decimal
            new_sender_saldo = current_sender_saldo - amount_to_transfer
            new_recipient_saldo = recipient_current_saldo + amount_to_transfer

            # Actualizar el saldo del emisor, convirtiendo de nuevo a Decimal128 para MongoDB
            collection.update_one(
                {'usuario': current_username},
                {'$set': {'saldo': Decimal128(str(new_sender_saldo))}}
            )

            # Actualizar el saldo del receptor, convirtiendo de nuevo a Decimal128 para MongoDB
            collection.update_one(
                {'usuario': recipient_username},
                {'$set': {'saldo': Decimal128(str(new_recipient_saldo))}}
            )

            flash(f"Transferencia de ${amount_to_transfer:.2f} a '{recipient_username}' realizada con éxito.", "success")
            return redirect(url_for('transferir_saldo'))

        except Exception as e:
            flash(f"Ocurrió un error al procesar la transferencia: {e}", "error")
            # En un entorno de producción, aquí se podría añadir lógica para revertir
            # las operaciones si la base de datos no soporta transacciones atómicas entre documentos.
            return redirect(url_for('transferir_saldo', search_query=search_query))

    # Renderizar la plantilla con el saldo actual del usuario (convertido a float para display) y los resultados de la búsqueda
    return render_template('transferir_saldo.html', 
                           saldo=float(current_sender_saldo), # Convertir a float para display en HTML
                           found_recipients=found_recipients, 
                           search_query=search_query,
                           usuario=current_username, # Pasando el nombre de usuario actual
                           foto_id=foto_id_current_user) # Pasando la foto_id del usuario actual



@app.route("/faq")
def faq():
    return render_template("faq.html")

    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)