from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify, send_file, send_from_directory
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus, urlparse, parse_qs, unquote_plus
import requests
import datetime
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from bson import Decimal128, ObjectId
from decimal import Decimal
import subprocess
import yt_dlp
import traceback
import uuid
import tempfile
import shutil
import re
from werkzeug.utils import secure_filename
import gridfs
from io import BytesIO
import qrcode
import io
from bson.json_util import dumps
from yoursmm import Api
import sys
from functools import wraps
import json
# Cargar variables de entorno
load_dotenv()

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'advpjsh')
bcrypt = Bcrypt(app)

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

limiter.init_app(app)


# Configuración de MongoDB
def init_mongodb():
    username = quote_plus(os.getenv('MONGO_USERNAME'))
    password = quote_plus(os.getenv('MONGO_PASSWORD'))
    client = MongoClient(f"mongodb+srv://{username}:{password}@cluster0.hx8un.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    
    db = client['db1']
    return {
        'usuarios': db['usuarios'],
        'pedidos': db['Pedidos'],
        'pagos': db['Pagos'],
        'articulos': db['articulos'],
        'streaming': db['streaming'],
        'soporte': db['soporteMensajes'],
        'freefire': db['diamantes'],
        'anuncios_vistas': db['anunciosVistas'],
        'fs': gridfs.GridFS(db)
    }

collections = init_mongodb()

# Configuraciones
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

serializer = URLSafeTimedSerializer(app.secret_key)

# Utilidades
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def decimal128_to_float(value):
    """Convierte Decimal128 a float de manera segura"""
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    elif isinstance(value, Decimal):
        return float(value)
    return float(value) if value is not None else 0.0

def obtener_saldo(usuario):
    """Obtiene el saldo del usuario convertido a float"""
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    if not user_data:
        return 0.0
    return decimal128_to_float(user_data.get('saldo', 0))

def enviar_email(destinatario, asunto, cuerpo):
    """Envía email usando SendGrid"""
    try:
        mensaje = Mail(
            from_email='kinghostshop88@gmail.com',
            to_emails=destinatario,
            subject=asunto,
            html_content=cuerpo
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(mensaje)
        print(f"Correo enviado con éxito! Status code: {response.status_code}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        flash("Error al enviar el correo, inténtalo más tarde.", "error")

def delete_expired_payments():
    """Elimina pagos pendientes expirados (más de 24 horas)"""
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    result = collections['pagos'].delete_many({
        'estado': 'pendiente',
        'fecha_creacion': {'$lt': time_threshold}
    })
    if result.deleted_count > 0:
        print(f"Se eliminaron {result.deleted_count} pagos pendientes expirados.")

# Decoradores
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        
        user_data = collections['usuarios'].find_one({'usuario': session['usuario']})
        if not user_data or user_data.get('rol') != 'admin':
            return redirect(url_for('pagina_principal'))
        return f(*args, **kwargs)
    return decorated_function

def check_ban(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' in session:
            user_data = collections['usuarios'].find_one({'usuario': session['usuario']})
            if user_data and user_data.get('ban') == 'ban':
                razon_ban = user_data.get('razon_ban', 'Razón no especificada')
                return render_template('ban.html', razon_ban=razon_ban)
        return f(*args, **kwargs)
    return decorated_function

# Rutas principales
@app.route("/")
def inicios():
    posts_list = collections['articulos'].find()
    return render_template('inicio.html', posts=posts_list)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if 'usuario' in session:
        user_data = collections['usuarios'].find_one({'usuario': session['usuario']})
        if user_data:
            if user_data.get('ban') == 'ban':
                razon_ban = user_data.get('razon_ban', 'Razón no especificada')
                return render_template('ban.html', razon_ban=razon_ban)
            if user_data.get('rol') == 'admin':
                return redirect(url_for('admin_inicio'))
            return redirect(url_for('pagina_principal'))

    if request.method == 'POST':
        username = request.form.get('usuario', '').strip()
        password = request.form.get('contrasena', '').strip()

        if not username or not password:
            flash("Por favor, ingresa ambos campos.", "error")
            return render_template('login.html')

        user_data = collections['usuarios'].find_one({'usuario': username})
        if user_data and bcrypt.check_password_hash(user_data['contrasena'], password):
            if user_data.get('ban') == 'ban':
                razon_ban = user_data.get('razon_ban', 'Razón no especificada')
                return render_template('ban.html', razon_ban=razon_ban)

            session['usuario'] = username
            session.permanent = 'remember' in request.form
            flash("Bienvenido de nuevo!", "success")
            
            if user_data.get('rol') == 'admin':
                return redirect(url_for('admin_inicio'))
            return redirect(url_for('pagina_principal'))
        else:
            flash("Usuario o contraseña incorrectos. Intenta de nuevo.", "error")

    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    referral_code = request.args.get('ref')

    if request.method == 'POST':
        data = {
            'nombre': request.form.get('name', '').strip(),
            'usuario': request.form.get('username', '').strip(),
            'whatsapp_country': request.form.get('whatsapp_country', '').strip(),
            'whatsapp_number': request.form.get('whatsapp_number', '').strip(),
            'email': request.form.get('email', '').strip(),
            'password': request.form.get('password', ''),
            'password_confirmation': request.form.get('password_confirmation', ''),
            'referral_code': request.form.get('referral_code', '').strip()
        }

        # Validaciones
        if data['password'] != data['password_confirmation']:
            flash("Las contraseñas no coinciden.")
            return redirect(url_for('registro', ref=referral_code or data['referral_code']))

        if collections['usuarios'].find_one({'email': data['email']}):
            flash("El correo electrónico ya está registrado.")
            return redirect(url_for('registro', ref=referral_code or data['referral_code']))

        if collections['usuarios'].find_one({'usuario': data['usuario']}):
            flash("El nombre de usuario ya está en uso.")
            return redirect(url_for('registro', ref=referral_code or data['referral_code']))

        final_referral_code = referral_code or data['referral_code']
        if final_referral_code and not collections['usuarios'].find_one({'codigo_referido': final_referral_code}):
            flash("El código de referido no es válido.")
            return redirect(url_for('registro'))

        # Generar código único de referido
        base_codigo = data['usuario']
        counter = 1
        codigo_referido = f"{base_codigo}_{counter}"
        while collections['usuarios'].find_one({'codigo_referido': codigo_referido}):
            counter += 1
            codigo_referido = f"{base_codigo}_{counter}"

        # Crear usuario
        whatsapp = f"+{data['whatsapp_country']}{data['whatsapp_number']}"
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        nuevo_usuario = {
            'nombre': data['nombre'],
            'usuario': data['usuario'],
            'whatsapp': whatsapp,
            'email': data['email'],
            'contrasena': hashed_password,
            'saldo': Decimal128('0'),
            'rol': 'user',
            'ban': 'no_ban',
            'razon_ban': '',
            'fecha_registro': datetime.utcnow(),
            'referido_por': final_referral_code if final_referral_code else None,
            'codigo_referido': codigo_referido,
            'enlace_referido': f"https://ghostsmm.shop/registro?ref={codigo_referido}"
        }

        collections['usuarios'].insert_one(nuevo_usuario)
        session['usuario'] = data['usuario']

        enviar_email(
            data['email'],
            "Bienvenido a nuestra plataforma",
            f"Hola {data['nombre']}, ¡bienvenido a nuestra plataforma! Para agregar fondos a tu cuenta, comunícate por WhatsApp al número +52 4661002589"
        )

        return redirect(url_for('pagina_principal'))

    return render_template('register.html', referral_code=referral_code)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash("Has cerrado sesión con éxito.", "info")
    return redirect(url_for('login'))

@app.route('/pagina_principal')
@login_required
@check_ban
def pagina_principal():
    user_data = collections['usuarios'].find_one({'usuario': session['usuario']})
    if not user_data:
        session.clear()
        return redirect(url_for('login'))

    saldo = decimal128_to_float(user_data.get('saldo', 0))
    foto_id = user_data.get('foto_id')
    mi_codigo = user_data.get('codigo_referido')
    enlace_referido = user_data.get('enlace_referido')

    # Obtener servicios de la API
    api = Api()
    try:
        categories_response = api.categories()
        services_response = api.services()
        
        categories = categories_response.get('categories', []) if isinstance(categories_response, dict) else categories_response or []
        services = services_response.get('services', []) if isinstance(services_response, dict) else services_response or []
        
        categories = [c for c in categories if c and isinstance(c, dict)]
        services = [s for s in services if s and isinstance(s, dict)]
    except Exception as e:
        print(f"Error obteniendo datos de API: {e}")
        categories, services = [], []

    # Obtener referidos
    referidos = []
    if mi_codigo:
        cursor = collections['usuarios'].find({'referido_por': mi_codigo})
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
                'foto_id': doc.get('foto_id')
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

@app.route('/mi_perfil', methods=['GET', 'POST'])
@login_required
def mi_perfil():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    saldo = decimal128_to_float(user_data.get('saldo', 0))

    if request.method == 'POST':
        if 'change-whatsapp' in request.form:
            new_whatsapp = request.form['new-whatsapp'].strip()
            if new_whatsapp:
                collections['usuarios'].update_one({'usuario': usuario}, {'$set': {'whatsapp': new_whatsapp}})
                flash("Número de WhatsApp actualizado con éxito.", "success")
            else:
                flash("El número de WhatsApp no puede estar vacío.", "error")

        elif 'change-password' in request.form:
            current_password = request.form['current-password']
            new_password = request.form['new-password']
            confirm_new_password = request.form['confirm-new-password']

            if not bcrypt.check_password_hash(user_data['contrasena'], current_password):
                flash("Contraseña actual incorrecta.", "error")
            elif new_password != confirm_new_password:
                flash("Las contraseñas no coinciden.", "error")
            else:
                hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                collections['usuarios'].update_one({'usuario': usuario}, {'$set': {'contrasena': hashed_password}})
                flash("Contraseña cambiada con éxito.", "success")

        elif 'change-email' in request.form:
            new_email = request.form['new-email']
            current_password_email = request.form['current-password-email']

            if not bcrypt.check_password_hash(user_data['contrasena'], current_password_email):
                flash("Contraseña incorrecta.", "error")
            elif collections['usuarios'].find_one({'email': new_email}):
                flash("Este correo electrónico ya está registrado.", "error")
            else:
                collections['usuarios'].update_one({'usuario': usuario}, {'$set': {'email': new_email}})
                flash("Correo electrónico cambiado con éxito.", "success")

        elif 'change-photo' in request.form and 'foto' in request.files:
            file = request.files['foto']
            if file and allowed_file(file.filename):
                # Eliminar foto anterior
                if user_data.get('foto_id'):
                    try:
                        collections['fs'].delete(ObjectId(user_data['foto_id']))
                    except Exception as e:
                        print(f"Error al eliminar la foto anterior: {e}")

                # Guardar nueva imagen
                file_id = collections['fs'].put(file, filename=file.filename, content_type=file.content_type)
                collections['usuarios'].update_one({'usuario': usuario}, {'$set': {'foto_id': file_id}})
                session['foto_id'] = str(file_id)
                flash("Foto de perfil actualizada.", "success")
            else:
                flash("Formato de imagen no permitido. Usa PNG, JPG, JPEG o GIF.", "error")

        return redirect(url_for('mi_perfil'))

    foto_id = user_data.get('foto_id')
    session['foto_id'] = str(foto_id) if foto_id else None

    return render_template('mi_perfil.html',
                         whatsapp=user_data.get('whatsapp', ''),
                         usuario=user_data['usuario'],
                         email=user_data['email'],
                         foto_id=foto_id,
                         saldo=saldo)

@app.route('/foto_perfil/<foto_id>')
def foto_perfil(foto_id):
    try:
        file = collections['fs'].get(ObjectId(foto_id))
        return send_file(BytesIO(file.read()), mimetype=file.content_type)
    except Exception as e:
        print(f"Error al obtener la foto: {e}")
        return send_file('static/fotos_perfil/default.jpg', mimetype='image/jpeg')

# Rutas de saldo y pagos
@app.route('/saldo', methods=['GET', 'POST'])
@login_required
def saldo():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))

    if request.method == 'POST':
        try:
            monto = float(request.form['monto'])
            metodo_pago = request.form['metodo_pago']

            collections['pagos'].insert_one({
                'usuario': usuario,
                'monto': Decimal128(str(monto)),
                'metodo_pago': metodo_pago,
                'estado': 'pendiente',
                'fecha_creacion': datetime.utcnow()
            })

            flash("Pago guardado correctamente. El estado es 'pendiente'.", "success")
        except Exception as e:
            flash(f"Hubo un error al procesar tu pago: {e}", "error")

        return redirect(url_for('saldo'))

    return render_template('saldo.html', usuario=usuario, saldo=saldo, foto_id=foto_id)

@app.route('/guardar_pago', methods=['POST'])
def guardar_pago():
    try:
        data = request.get_json()
        collections['pagos'].insert_one({
            'usuario': data['usuario'],
            'monto': Decimal128(str(data['monto'])),
            'metodo_pago': data['metodo_pago'],
            'estado': data.get('estado', 'pendiente'),
            'fecha_creacion': datetime.utcnow()
        })
        return jsonify({'success': True, 'message': 'Pago guardado exitosamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/movimientos')
@login_required
def movimientos():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))

    movimientos_usuario = collections['pagos'].find({'usuario': usuario})
    pagos = []
    
    for pago in movimientos_usuario:
        monto = decimal128_to_float(pago.get('monto', 0))
        pagos.append({
            'descripcion': pago.get('metodo_pago', 'Desconocido'),
            'monto': round(monto, 2),
            'estado': pago.get('estado', 'pendiente'),
            'fecha': pago.get('fecha_creacion', datetime.utcnow()).strftime('%Y-%m-%d')
        })
    
    return render_template('mov.html', usuario=usuario, pagos=pagos, foto_id=foto_id, saldo=saldo)

# Rutas de pedidos
@app.route('/agregar_orden', methods=['GET', 'POST'])
@login_required
def agregar_orden():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    saldo = decimal128_to_float(user_data.get('saldo', 0))
    foto_id = user_data.get('foto_id')

    api = Api()
    try:
        categories_response = api.categories()
        services_response = api.services()
        
        categories = categories_response.get('categories', []) if isinstance(categories_response, dict) else categories_response or []
        services = services_response.get('services', []) if isinstance(services_response, dict) else services_response or []
        
        categories = [c for c in categories if c and isinstance(c, dict)]
        services = [s for s in services if s and isinstance(s, dict)]
    except Exception as e:
        print(f"Error obteniendo datos de API: {e}")
        categories, services = [], []

    if saldo <= 0:
        flash("Saldo Insuficiente. No tienes saldo suficiente para realizar pedidos.", "error")
        return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services, foto_id=foto_id)

    if request.method == 'POST':
        cantidad = int(request.form['quantity'])
        servicio_id = request.form['service']
        enlace = request.form['link']

        servicio = next((s for s in services if s['service'] == servicio_id), None)

        if servicio:
            precio_por_unidad = float(servicio.get('rate', 0)) * 1.40
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
                        estado_response = api.get_order_status(order_id)
                        estado = estado_response.get('status', 'Pending').capitalize() if estado_response else 'Pending'

                        collections['pedidos'].insert_one({
                            'usuario': usuario,
                            'cantidad': cantidad,
                            'monto': monto,
                            'estado': estado,
                            'order_id': order_id,
                            'fecha': datetime.utcnow()
                        })

                        # Actualizar saldo
                        nuevo_saldo = saldo - monto
                        collections['usuarios'].update_one(
                            {'usuario': usuario}, 
                            {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
                        )

                        flash("Pedido creado con éxito. Puedes hacer otro pedido.", "success")
                    else:
                        flash("Hubo un problema al crear el pedido", "error")
                except Exception as e:
                    flash("Error al realizar el pedido. Intenta más tarde.", "error")
            else:
                flash("No tienes suficiente saldo para realizar esta orden.", "error")

        return redirect(url_for('agregar_orden'))

    return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services, foto_id=foto_id)

@app.route('/pedidos')
@login_required
def ver_pedidos():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    saldo = decimal128_to_float(user_data.get('saldo', 0))
    foto_id = user_data.get('foto_id')

    pedidos = collections['pedidos'].find({'usuario': usuario})
    api = Api()

    # Actualizar estados de pedidos
    for pedido in pedidos:
        order_id = pedido.get('order_id')
        if order_id:
            try:
                estado_actual = api.get_order_status(order_id)
                if estado_actual and 'status' in estado_actual:
                    nuevo_estado = estado_actual['status'].capitalize()
                    if pedido['estado'] != nuevo_estado:
                        collections['pedidos'].update_one(
                            {'_id': pedido['_id']},
                            {'$set': {'estado': nuevo_estado}}
                        )
            except Exception as e:
                print(f"Error al obtener el estado del pedido {order_id}: {e}")

    # Volver a consultar pedidos actualizados
    pedidos = collections['pedidos'].find({'usuario': usuario})
    return render_template('pedidos.html', usuario=usuario, saldo=saldo, pedidos=pedidos, foto_id=foto_id)

# Rutas de administración
@app.route('/admin')
@admin_required
def admin_dashboard():
    delete_expired_payments()

    # Obtener usuarios
    usuarios_cursor = collections['usuarios'].find()
    usuarios_list = []
    for user in usuarios_cursor:
        user['saldo'] = decimal128_to_float(user.get('saldo', 0))
        usuarios_list.append(user)

    # Filtrar por búsqueda
    query = request.args.get('query')
    if query:
        usuarios_list = [u for u in usuarios_list 
                        if query.lower() in u.get('usuario', '').lower() or 
                           query.lower() in u.get('email', '').lower()]

    # Obtener pagos pendientes
    pagos_cursor = collections['pagos'].find({'estado': 'pendiente'})
    pagos_list = []
    for pago in pagos_cursor:
        pago['monto'] = decimal128_to_float(pago.get('monto', 0))
        pagos_list.append(pago)

    return render_template('admin.html', usuarios=usuarios_list, pagos=pagos_list)

@app.route('/admin_inicio')
@admin_required
def admin_inicio():
    return render_template('admin_inicio.html')

# Rutas de recuperación de contraseña
@app.route('/recuperar_contrasena', methods=['GET', 'POST'])
def recuperar_contrasena():
    if request.method == 'POST':
        email = request.form['email']
        usuario = collections['usuarios'].find_one({'email': email})

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
        collections['usuarios'].update_one({'email': email}, {'$set': {'contrasena': hashed_password}})
        flash("Tu contraseña ha sido restablecida con éxito.", "success")
        return redirect(url_for('login'))

    return render_template('restablecer_contrasena.html')

# Rutas adicionales (streaming, diamantes, etc.)
@app.route('/streaming', methods=['GET', 'POST'])
def streaming():
    logueado = 'usuario' in session
    if logueado:
        user_data = collections['usuarios'].find_one({'usuario': session['usuario']})
        if user_data and user_data.get('ban') == 'ban':
            return render_template('ban.html', razon_ban=user_data.get('razon_ban', 'Sin razón'))
        
        return render_template('streaming.html', 
                             logueado=True, 
                             usuario=user_data['usuario'], 
                             saldo=decimal128_to_float(user_data.get('saldo', 0)),
                             foto_id=user_data.get('foto_id'))
    
    return render_template('streaming.html', logueado=False)

@app.route('/comprar', methods=['POST'])
@login_required
def comprar():
    try:
        data = request.get_json()
        user_data = collections['usuarios'].find_one({'usuario': session['usuario']})
        
        servicio = data.get('servicio')
        precio = Decimal(str(data.get('precio')))
        nombre = data.get('nombre')
        whatsapp = data.get('whatsapp')
        email = data.get('email', '')
        observaciones = data.get('observaciones', '')

        saldo_actual = Decimal(str(decimal128_to_float(user_data.get('saldo', 0))))

        if saldo_actual >= precio:
            nuevo_saldo = saldo_actual - precio

            collections['usuarios'].update_one(
                {'usuario': session['usuario']},
                {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
            )

            collections['streaming'].insert_one({
                'usuario': session['usuario'],
                'servicio': servicio,
                'precio': float(precio),
                'nombre': nombre,
                'whatsapp': whatsapp,
                'email': email,
                'observaciones': observaciones,
                'fecha': datetime.utcnow(),
                'estado': 'pendiente'
            })

            return jsonify({
                'message': f'Has comprado {servicio} correctamente. En menos de 24 horas te enviaremos los detalles por WhatsApp. Tu nuevo saldo es ${nuevo_saldo:.2f}'
            }), 200
        else:
            return jsonify({'message': 'Saldo insuficiente'}), 400

    except Exception as e:
        print(f"Error en compra: {e}")
        return jsonify({'message': 'Error interno del servidor'}), 500

@app.route('/pedidosStreaming')
@login_required
def ver_pedidos_streaming():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))
    
    pedidos = list(collections['streaming'].find({'usuario': usuario}).sort('_id', -1))
    
    return render_template('Streamingpedidos.html', 
                         pedidos=pedidos,
                         usuario=usuario,
                         saldo=saldo,
                         foto_id=foto_id)

@app.route('/diamantes')
@login_required
def diamantes():
    user_data = collections['usuarios'].find_one({'usuario': session['usuario']})
    saldo = decimal128_to_float(user_data.get('saldo', 0))
    foto_id = user_data.get('foto_id')

    return render_template('diamantes.html', 
                         logueado=True, 
                         usuario=user_data['usuario'], 
                         saldo=saldo,
                         foto_id=foto_id)

@app.route('/free-fire-diamonds', methods=['POST'])
@login_required
def guardar_diamantes():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Datos incompletos'}), 400

    try:
        # Precios en USD
        precios = {
            "520 + 52 Diamantes Bonus": Decimal('4.87'),
            "620 + 62 Diamantes Bonus": Decimal('5.64'),
            "830 + 80 Diamantes Bonus": Decimal('7.95'),
            "1060 + 106 Diamantes Bonus": Decimal('9.74'),
            "2180 + 218 Diamantes Bonus": Decimal('18.46'),
            "4360 + 436 Diamantes Bonus": Decimal('37.18'),
            "5600 + 560 Diamantes Bonus": Decimal('46.15'),
            "Tarjeta Semanal": Decimal('1.9'),
            "Tarjeta Mensual": Decimal('9.25')
        }

        paquete = data.get("paquete")
        precio = precios.get(paquete)
        
        if precio is None:
            return jsonify({'success': False, 'error': 'Paquete no válido'}), 400

        user = collections['usuarios'].find_one({'usuario': session['usuario']})
        if not user:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

        saldo_actual = Decimal(str(decimal128_to_float(user.get('saldo', 0))))

        if saldo_actual < precio:
            return jsonify({'success': False, 'error': 'Saldo insuficiente'}), 400

        nuevo_saldo = saldo_actual - precio
        collections['usuarios'].update_one(
            {'usuario': session['usuario']},
            {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
        )

        collections['freefire'].insert_one({
            'usuario': session['usuario'],
            'nombre': data.get("nombre"),
            'whatsapp': data.get("whatsapp"),
            'nick': data.get("nick"),
            'idJuego': data.get("idJuego"),
            'paquete': paquete,
            'precio': float(precio),
            'fecha': datetime.utcnow(),
            'estado': 'Pendiente'
        })

        return jsonify({
            'success': True, 
            'message': f'Compra realizada correctamente. Tu nuevo saldo es ${nuevo_saldo:.2f}',
            'redirect': url_for('diamantes')
        })

    except Exception as e:
        print(f"Error en diamantes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/historial-recargas')
@login_required
def historial_recargas():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))

    recargas_cursor = collections['freefire'].find({'usuario': usuario}).sort('fecha', -1)
    recargas = []
    
    for recarga in recargas_cursor:
        recarga['precio'] = decimal128_to_float(recarga.get('precio', 0))
        if isinstance(recarga.get('fecha'), datetime):
            recarga['fecha'] = recarga['fecha'].strftime('%Y-%m-%d %H:%M:%S')
        recarga['estado'] = recarga.get('estado', 'Pendiente')
        recargas.append(recarga)

    return render_template('historial_recargas.html', 
                         logueado=True, 
                         usuario=usuario, 
                         recargas=recargas,
                         saldo=saldo,
                         foto_id=foto_id)

@app.route('/transferir_saldo', methods=['GET', 'POST'])
@login_required
def transferir_saldo():
    current_username = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': current_username})
    
    current_sender_saldo = Decimal(str(decimal128_to_float(user_data.get('saldo', 0))))
    foto_id_current_user = str(user_data.get('foto_id')) if user_data.get('foto_id') else None

    found_recipients = []
    search_query = request.args.get('search_query')

    if search_query:
        search_results_cursor = collections['usuarios'].find({
            '$and': [
                {'$or': [
                    {'usuario': {'$regex': search_query, '$options': 'i'}},
                    {'email': {'$regex': search_query, '$options': 'i'}}
                ]},
                {'usuario': {'$ne': current_username}}
            ]
        })
        
        for user in search_results_cursor:
            found_recipients.append({
                'usuario': user.get('usuario'),
                'email': user.get('email'),
                'foto_id': str(user.get('foto_id')) if user.get('foto_id') else None
            })

    if request.method == 'POST':
        recipient_username = request.form.get('recipient_username', '').strip()
        amount_str = request.form.get('amount', '').strip()

        try:
            amount_to_transfer = Decimal(amount_str)
        except:
            flash("Monto inválido. Por favor, ingresa un número válido.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        if amount_to_transfer <= Decimal('0'):
            flash("El monto a transferir debe ser mayor que cero.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        if current_sender_saldo < amount_to_transfer:
            flash("Saldo insuficiente para realizar esta transferencia.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        if recipient_username == current_username:
            flash("No puedes transferir saldo a tu propia cuenta.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        recipient_data = collections['usuarios'].find_one({'usuario': recipient_username})
        if not recipient_data:
            flash(f"El usuario '{recipient_username}' no existe.", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

        try:
            recipient_current_saldo = Decimal(str(decimal128_to_float(recipient_data.get('saldo', 0))))
            
            new_sender_saldo = current_sender_saldo - amount_to_transfer
            new_recipient_saldo = recipient_current_saldo + amount_to_transfer

            collections['usuarios'].update_one(
                {'usuario': current_username},
                {'$set': {'saldo': Decimal128(str(new_sender_saldo))}}
            )

            collections['usuarios'].update_one(
                {'usuario': recipient_username},
                {'$set': {'saldo': Decimal128(str(new_recipient_saldo))}}
            )

            flash(f"Transferencia de ${amount_to_transfer:.2f} a '{recipient_username}' realizada con éxito.", "success")
            return redirect(url_for('transferir_saldo'))

        except Exception as e:
            flash(f"Ocurrió un error al procesar la transferencia: {e}", "error")
            return redirect(url_for('transferir_saldo', search_query=search_query))

    return render_template('transferir_saldo.html', 
                         saldo=float(current_sender_saldo),
                         found_recipients=found_recipients, 
                         search_query=search_query,
                         usuario=current_username,
                         foto_id=foto_id_current_user)

@app.route('/soporte', methods=['GET', 'POST'])
@login_required
def soporte():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))

    if request.method == 'POST':
        asunto = request.form.get('asunto')
        mensaje = request.form.get('mensaje')

        collections['soporte'].insert_one({
            'usuario': usuario,
            'asunto': asunto,
            'mensaje': mensaje,
            'fecha': datetime.utcnow()
        })

        flash("Tu mensaje ha sido enviado. Te responderemos pronto.", "success")
        return redirect(url_for('soporte'))

    return render_template('soporte.html', usuario=usuario, saldo=saldo, foto_id=foto_id)

# Rutas administrativas adicionales
@app.route('/admin_soporte')
@admin_required
def admin_soporte():
    mensajes = list(collections['soporte'].find().sort('fecha', -1))
    return render_template('admin_soporte.html', mensajes=mensajes)

@app.route('/admin_streaming')
@admin_required
def admin_streaming():
    estado = request.args.get('estado')
    filtro = {'estado': estado} if estado in ('pendiente', 'entregado') else {}
    
    pedidos = [
        {**p, '_id': str(p['_id'])} 
        for p in collections['streaming'].find(filtro).sort('_id', -1)
    ]
    
    return render_template('admin_streaming.html', pedidos=pedidos, filtro_estado=estado or '')

@app.route('/marcar_entregado/<pedido_id>', methods=['POST'])
@admin_required
def marcar_entregado(pedido_id):
    collections['streaming'].update_one(
        {'_id': ObjectId(pedido_id)},
        {'$set': {'estado': 'entregado'}}
    )
    return redirect(url_for('admin_streaming'))

@app.route('/admin_diamantes')
@admin_required
def admin_diamantes():
    estado_filtro = request.args.get('estado')
    filtro_db = {'estado': estado_filtro.capitalize()} if estado_filtro else {}

    pedidos_cursor = collections['freefire'].find(filtro_db).sort('fecha', -1)
    pedidos = []
    
    for pedido in pedidos_cursor:
        pedido['_id'] = str(pedido['_id'])
        pedido['precio'] = decimal128_to_float(pedido.get('precio', 0))
        if isinstance(pedido.get('fecha'), datetime):
            pedido['fecha'] = pedido['fecha'].strftime('%Y-%m-%d %H:%M:%S')
        pedido['estado'] = pedido.get('estado', 'Pendiente')
        pedidos.append(pedido)

    return render_template('admin_diamantes.html', 
                         logueado=True, 
                         usuario=session['usuario'], 
                         pedidos=pedidos,
                         filtro_estado=estado_filtro or '')

@app.route('/admin/diamantes/update_status', methods=['POST'])
@admin_required
def update_diamantes_status():
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Content-Type debe ser application/json.'}), 400

    data = request.get_json()
    order_id_str = data.get('order_id')
    new_status = data.get('status')

    if not order_id_str or not new_status:
        return jsonify({'success': False, 'error': 'Datos incompletos.'}), 400

    try:
        result = collections['freefire'].update_one(
            {'_id': ObjectId(order_id_str)},
            {'$set': {'estado': new_status}}
        )

        if result.matched_count > 0:
            return jsonify({'success': True, 'message': 'Estado actualizado.'}), 200
        else:
            return jsonify({'success': False, 'error': 'Pedido no encontrado.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/diamantes/delete', methods=['POST'])
@admin_required
def delete_diamante_order():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Datos incompletos.'}), 400

    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'ID de pedido no proporcionado.'}), 400

    try:
        result = collections['freefire'].delete_one({'_id': ObjectId(order_id)})
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': f'Pedido {order_id} eliminado correctamente.'})
        else:
            return jsonify({'success': False, 'error': f'Pedido {order_id} no encontrado.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Rutas de administración de pagos
@app.route('/actualizar_pago', methods=['POST'])
@admin_required
def actualizar_pago():
    try:
        pago_id = request.form['pago_id']
        nuevo_estado = request.form['nuevo_estado']

        pago = collections['pagos'].find_one({'_id': ObjectId(pago_id)})
        if not pago:
            flash("Pago no encontrado.", "error")
            return redirect(url_for('admin_dashboard'))

        collections['pagos'].update_one({'_id': ObjectId(pago_id)}, {'$set': {'estado': nuevo_estado}})

        if nuevo_estado == 'completado':
            usuario_pago = pago.get('usuario')
            monto_pago = decimal128_to_float(pago.get('monto', 0))

            if usuario_pago and monto_pago > 0:
                user_data = collections['usuarios'].find_one({'usuario': usuario_pago})
                saldo_actual = decimal128_to_float(user_data.get('saldo', 0))
                nuevo_saldo = saldo_actual + monto_pago
                
                collections['usuarios'].update_one(
                    {'usuario': usuario_pago}, 
                    {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
                )
                flash(f"Pago de {usuario_pago} completado y saldo actualizado.", "success")
            else:
                flash("No se pudo obtener la información del usuario o monto del pago.", "error")
        else:
            flash("Estado del pago actualizado exitosamente.", "success")

        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        flash(f"Hubo un error al actualizar el estado del pago: {e}", "error")
        return redirect(url_for('admin_dashboard'))

# Actualización masiva de acciones de admin
@app.route('/admin', methods=['POST'])
@admin_required
def admin_actions():
    accion = request.form.get('accion')
    usuario_a_modificar = request.form.get('usuario')
    
    try:
        if accion == 'agregar_saldo':
            saldo_adicional = float(request.form['monto'])
            user_data = collections['usuarios'].find_one({'usuario': usuario_a_modificar})
            saldo_actual = decimal128_to_float(user_data.get('saldo', 0))
            nuevo_saldo = saldo_actual + saldo_adicional
            
            collections['usuarios'].update_one(
                {'usuario': usuario_a_modificar}, 
                {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
            )
            flash(f"Saldo de {usuario_a_modificar} actualizado en {saldo_adicional} unidades.", "success")

        elif accion == 'quitar_saldo':
            saldo_reducido = float(request.form['monto'])
            user_data = collections['usuarios'].find_one({'usuario': usuario_a_modificar})
            saldo_actual = decimal128_to_float(user_data.get('saldo', 0))
            nuevo_saldo = max(0, saldo_actual - saldo_reducido)  # No permitir saldo negativo
            
            collections['usuarios'].update_one(
                {'usuario': usuario_a_modificar}, 
                {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
            )
            flash(f"Saldo de {usuario_a_modificar} reducido en {saldo_reducido} unidades.", "success")

        elif accion == 'cambiar_usuario':
            new_username = request.form['nuevo_valor'].strip()
            if new_username and not collections['usuarios'].find_one({'usuario': new_username}):
                collections['usuarios'].update_one(
                    {'usuario': usuario_a_modificar}, 
                    {'$set': {'usuario': new_username}}
                )
                flash("Nombre de usuario actualizado.", "success")
            else:
                flash("El nombre de usuario no puede estar vacío o ya existe.", "error")

        elif accion == 'cambiar_email':
            nuevo_email = request.form['nuevo_valor'].strip()
            if nuevo_email and not collections['usuarios'].find_one({'email': nuevo_email}):
                collections['usuarios'].update_one(
                    {'usuario': usuario_a_modificar}, 
                    {'$set': {'email': nuevo_email}}
                )
                flash("Correo electrónico actualizado.", "success")
            else:
                flash("El correo electrónico no puede estar vacío o ya existe.", "error")

        elif accion == 'cambiar_contrasena':
            nueva_contrasena = request.form['nuevo_valor']
            if nueva_contrasena:
                hashed_password = bcrypt.generate_password_hash(nueva_contrasena).decode('utf-8')
                collections['usuarios'].update_one(
                    {'usuario': usuario_a_modificar}, 
                    {'$set': {'contrasena': hashed_password}}
                )
                flash("Contraseña actualizada.", "success")
            else:
                flash("La nueva contraseña no puede estar vacía.", "error")

        elif accion == 'banear_usuario':
            razon = request.form.get('razon_ban', '').strip()
            if razon:
                collections['usuarios'].update_one(
                    {'usuario': usuario_a_modificar}, 
                    {'$set': {'ban': 'ban', 'razon_ban': razon}}
                )
                flash(f"El usuario {usuario_a_modificar} ha sido baneado.", "success")
            else:
                flash("Debes proporcionar una razón para el ban.", "error")
        
        elif accion == 'desbanear_usuario':
            collections['usuarios'].update_one(
                {'usuario': usuario_a_modificar}, 
                {'$set': {'ban': 'no_ban', 'razon_ban': ''}}
            )
            flash(f"El usuario {usuario_a_modificar} ha sido desbloqueado.", "success")

    except ValueError:
        flash("El valor ingresado no es válido.", "error")
    except Exception as e:
        flash(f"Error al procesar la acción: {e}", "error")

    return redirect(url_for('admin_dashboard'))

# Rutas de gestión de posts
@app.route("/admin_post")
@admin_required
def admin_post():
    return render_template("admin_post.html", posts=collections['articulos'].find())

@app.route("/admin_post/nuevo", methods=["POST"])
@admin_required
def nuevo_post():
    try:
        collections['articulos'].insert_one({
            "titulo": request.form["titulo"],
            "parrafo": request.form["parrafo"],
            "img": request.form["img"],
            "alt": request.form["alt"],
            "descripcion": request.form["descripcion"],
            "enlace_href": request.form["enlace_href"],
            "enlace_texto": request.form["enlace_texto"]
        })
        flash("Post creado con éxito", "success")
    except Exception as e:
        flash(f"Error al crear el post: {e}", "error")

    return redirect("/admin_post")

@app.route("/admin_post/editar/<id>", methods=["POST"])
@admin_required
def editar_post(id):
    try:
        collections['articulos'].update_one(
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
        flash("Post actualizado con éxito", "success")
    except Exception as e:
        flash(f"Error al actualizar el post: {e}", "error")
    
    return redirect("/admin_post")

@app.route("/admin_post/eliminar/<id>", methods=["POST"])
@admin_required
def eliminar_post(id):
    try:
        collections['articulos'].delete_one({"_id": ObjectId(id)})
        flash("Artículo eliminado con éxito", "success")
    except Exception as e:
        flash(f"Error al eliminar el artículo: {e}", "error")

    return redirect("/admin_post")

# Rutas auxiliares
@app.route('/ban')
def ban():
    usuario = session.get('usuario')
    if not usuario:
        return redirect(url_for('login'))

    user_data = collections['usuarios'].find_one({'usuario': usuario})
    razon_ban = 'No estás baneado'

    if user_data and user_data.get('ban') == 'ban':
        razon_ban = user_data.get('razon_ban', 'Sin razón especificada')

    return render_template('ban.html', razon_ban=razon_ban)

@app.route('/qrcode')
def generate_qrcode():
    return render_template('genqr.html')

# Rutas adicionales

@app.route('/tiktok')
def tiktok_page():
    return render_template("tiktok.html")

@app.route('/tiktok-download', methods=['POST'])
def tiktok_download():
    video_url = request.form.get('url')
    if not video_url:
        flash("Error: No se proporcionó una URL de TikTok.", "error")
        return redirect(url_for('tiktok_page'))

    try:
        api_url = "https://tikwm.com/api"
        response = requests.get(api_url, params={"url": video_url})
        data = response.json()

        if data["code"] != 0:
            
            flash(f"{data['msg']}", "error")
            return redirect(url_for('tiktok_page'))

        video_download_url = data["data"]["play"]
        video_content = requests.get(video_download_url).content
        filename = f"tiktok_{uuid.uuid4().hex}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)

        with open(filepath, "wb") as f:
            f.write(video_content)

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        flash(f"Ocurrió un error inesperado: {str(e)}", "error")
        return redirect(url_for('tiktok_page'))

# Rutas estáticas adicionales
@app.route("/imgcode")
def imgcode():
    return render_template('gencode.html')

@app.route("/ajedrez")
def ajedrez():
    return render_template('ajedres.html')

@app.route("/principal")
def smmprincipal():
    return render_template('principal.html')

@app.route("/faq")
def faq():
    return render_template("faq.html")




@app.route('/buscarXid', methods=['POST'])
def buscarFF():
    uid = request.form.get('uid')
    region = request.form.get('region', 'br')  # valor por defecto: US

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('Content-Type') == 'application/json' or \
              request.is_json

    node_script = os.path.abspath("get_player_data.js")
    print(f"Ejecutando script Node en: {node_script}")

    try:
        result = subprocess.run(
            ['node', node_script, uid, region],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )

        print("CODE:", result.returncode)
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)

        output = (result.stdout or "").strip()
        if not output:
            output = (result.stderr or "").strip()

        if not output:
            error_msg = "⚠️ El script no devolvió ninguna salida."
            if is_ajax:
                return jsonify({"success": False, "error": error_msg})
            return render_template('diamantes.html', error=error_msg, uid=uid)

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            error_msg = f"❌ La salida no es JSON válido: {output}"
            if is_ajax:
                return jsonify({"success": False, "error": error_msg})
            return render_template('diamantes.html', error=error_msg, uid=uid)

        if 'error' in data:
            if is_ajax:
                return jsonify({"success": False, "error": data['error']})
            return render_template('diamantes.html', error=data['error'], uid=uid)

        # Si llegamos aquí, la búsqueda fue exitosa
        if is_ajax:
            return jsonify({"success": True, "data": data})

        return render_template('diamantes.html', result=data, uid=uid)

    except subprocess.TimeoutExpired:
        error_msg = "❌ Tiempo de espera agotado. El servidor tardó demasiado en responder."
        if is_ajax:
            return jsonify({"success": False, "error": error_msg})
        return render_template('diamantes.html', error=error_msg, uid=uid)

    except Exception as e:
        error_msg = f"❌ Excepción inesperada: {str(e)}"
        if is_ajax:
            return jsonify({"success": False, "error": error_msg})
        return render_template('diamantes.html', error=error_msg, uid=uid)

@app.route("/terminos")
@login_required
def terminos():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))
    
    return render_template('terminos.html', usuario=usuario, saldo=saldo, foto_id=foto_id)

# Manejo de errores
@app.errorhandler(404)
def page_not_found(e):
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))
    
    return render_template('404.html', usuario=usuario, saldo=saldo, foto_id=foto_id), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# ================================
# SISTEMA DE ANUNCIOS RECOMPENSADOS
# ================================

# Primero, agregar esta línea en la función init_mongodb() después de 'freefire': db['diamantes'],
# 'anuncios_vistas': db['anunciosVistas'],

# Configuración de anuncios (agregar después de las otras configuraciones)
ANUNCIOS_CONFIG = {
    'recompensa_por_anuncio': 0.05,  # $0.05 por anuncio visto
    'limite_diario': 10,  # Máximo 10 anuncios recompensados por día
    'tiempo_minimo_vista': 10,  # 10 segundos mínimo de visualización
    'cooldown_entre_anuncios': 30  # 30 segundos entre anuncios
}

@app.route('/anuncios')
@login_required
@check_ban
def anuncios():
    usuario = session['usuario']
    user_data = collections['usuarios'].find_one({'usuario': usuario})
    foto_id = user_data.get('foto_id')
    saldo = decimal128_to_float(user_data.get('saldo', 0))
    
    # Obtener estadísticas del día actual
    hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    vistas_hoy = collections['anuncios_vistas'].count_documents({
        'usuario': usuario,
        'fecha': {'$gte': hoy}
    })
    
    # Calcular anuncios restantes
    anuncios_restantes = max(0, ANUNCIOS_CONFIG['limite_diario'] - vistas_hoy)
    
    # Obtener último anuncio visto para calcular cooldown
    ultimo_anuncio = collections['anuncios_vistas'].find_one(
        {'usuario': usuario},
        sort=[('fecha', -1)]
    )
    
    puede_ver_anuncio = True
    tiempo_espera = 0
    
    if ultimo_anuncio:
        tiempo_transcurrido = (datetime.utcnow() - ultimo_anuncio['fecha']).total_seconds()
        if tiempo_transcurrido < ANUNCIOS_CONFIG['cooldown_entre_anuncios']:
            puede_ver_anuncio = False
            tiempo_espera = int(ANUNCIOS_CONFIG['cooldown_entre_anuncios'] - tiempo_transcurrido)
    
    # Obtener historial de ganancias (últimos 30 días)
    hace_30_dias = datetime.utcnow() - timedelta(days=30)
    historial = list(collections['anuncios_vistas'].find({
        'usuario': usuario,
        'fecha': {'$gte': hace_30_dias}
    }).sort('fecha', -1).limit(50))
    
    # Calcular ganancias totales del mes
    ganancias_mes = collections['anuncios_vistas'].count_documents({
        'usuario': usuario,
        'fecha': {'$gte': hace_30_dias}
    }) * ANUNCIOS_CONFIG['recompensa_por_anuncio']
    
    return render_template('anuncios.html',
                         usuario=usuario,
                         saldo=saldo,
                         foto_id=foto_id,
                         vistas_hoy=vistas_hoy,
                         anuncios_restantes=anuncios_restantes,
                         puede_ver_anuncio=puede_ver_anuncio,
                         tiempo_espera=tiempo_espera,
                         recompensa=ANUNCIOS_CONFIG['recompensa_por_anuncio'],
                         tiempo_minimo=ANUNCIOS_CONFIG['tiempo_minimo_vista'],
                         historial=historial,
                         ganancias_mes=ganancias_mes)

@app.route('/ver_anuncio', methods=['POST'])
@login_required
@check_ban
@limiter.limit("1 per 30 seconds")
def ver_anuncio():
    try:
        data = request.get_json()
        usuario = session['usuario']
        tiempo_visto = data.get('tiempo_visto', 0)
        anuncio_id = data.get('anuncio_id', 'default')
        
        # Validaciones
        if tiempo_visto < ANUNCIOS_CONFIG['tiempo_minimo_vista']:
            return jsonify({
                'success': False, 
                'message': f'Debes ver el anuncio por al menos {ANUNCIOS_CONFIG["tiempo_minimo_vista"]} segundos'
            }), 400
        
        # Verificar límite diario
        hoy = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        vistas_hoy = collections['anuncios_vistas'].count_documents({
            'usuario': usuario,
            'fecha': {'$gte': hoy}
        })
        
        if vistas_hoy >= ANUNCIOS_CONFIG['limite_diario']:
            return jsonify({
                'success': False, 
                'message': 'Has alcanzado el límite diario de anuncios recompensados'
            }), 400
        
        # Verificar cooldown
        ultimo_anuncio = collections['anuncios_vistas'].find_one(
            {'usuario': usuario},
            sort=[('fecha', -1)]
        )
        
        if ultimo_anuncio:
            tiempo_transcurrido = (datetime.utcnow() - ultimo_anuncio['fecha']).total_seconds()
            if tiempo_transcurrido < ANUNCIOS_CONFIG['cooldown_entre_anuncios']:
                return jsonify({
                    'success': False, 
                    'message': f'Debes esperar {int(ANUNCIOS_CONFIG["cooldown_entre_anuncios"] - tiempo_transcurrido)} segundos antes del próximo anuncio'
                }), 400
        
        # Registrar la vista del anuncio
        collections['anuncios_vistas'].insert_one({
            'usuario': usuario,
            'anuncio_id': anuncio_id,
            'tiempo_visto': tiempo_visto,
            'recompensa': ANUNCIOS_CONFIG['recompensa_por_anuncio'],
            'fecha': datetime.utcnow(),
            'ip': request.remote_addr
        })
        
        # Actualizar saldo del usuario
        user_data = collections['usuarios'].find_one({'usuario': usuario})
        saldo_actual = decimal128_to_float(user_data.get('saldo', 0))
        nuevo_saldo = saldo_actual + ANUNCIOS_CONFIG['recompensa_por_anuncio']
        
        collections['usuarios'].update_one(
            {'usuario': usuario},
            {'$set': {'saldo': Decimal128(str(nuevo_saldo))}}
        )
        
        # Calcular nuevas estadísticas
        vistas_hoy_nuevo = vistas_hoy + 1
        anuncios_restantes = max(0, ANUNCIOS_CONFIG['limite_diario'] - vistas_hoy_nuevo)
        
        return jsonify({
            'success': True,
            'message': f'¡Felicidades! Has ganado ${ANUNCIOS_CONFIG["recompensa_por_anuncio"]:.2f}',
            'nuevo_saldo': round(nuevo_saldo, 2),
            'anuncios_restantes': anuncios_restantes,
            'vistas_hoy': vistas_hoy_nuevo,
            'cooldown': ANUNCIOS_CONFIG['cooldown_entre_anuncios']
        })
        
    except Exception as e:
        print(f"Error en ver_anuncio: {e}")
        return jsonify({
            'success': False, 
            'message': 'Error interno del servidor'
        }), 500

@app.route('/estadisticas_anuncios')
@login_required
def estadisticas_anuncios():
    usuario = session['usuario']
    
    # Estadísticas generales
    total_vistas = collections['anuncios_vistas'].count_documents({'usuario': usuario})
    total_ganancias = total_vistas * ANUNCIOS_CONFIG['recompensa_por_anuncio']
    
    # Estadísticas por mes (últimos 6 meses)
    estadisticas_mensuales = []
    for i in range(6):
        inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - relativedelta(months=i)
        fin_mes = inicio_mes + relativedelta(months=1)
        
        vistas_mes = collections['anuncios_vistas'].count_documents({
            'usuario': usuario,
            'fecha': {'$gte': inicio_mes, '$lt': fin_mes}
        })
        
        estadisticas_mensuales.append({
            'mes': inicio_mes.strftime('%B %Y'),
            'vistas': vistas_mes,
            'ganancias': vistas_mes * ANUNCIOS_CONFIG['recompensa_por_anuncio']
        })
    
    return jsonify({
        'total_vistas': total_vistas,
        'total_ganancias': round(total_ganancias, 2),
        'estadisticas_mensuales': estadisticas_mensuales
    })

@app.route('/admin_anuncios')
@admin_required
def admin_anuncios():
    # Estadísticas generales
    total_vistas_hoy = collections['anuncios_vistas'].count_documents({
        'fecha': {'$gte': datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
    })
    
    total_recompensas_hoy = total_vistas_hoy * ANUNCIOS_CONFIG['recompensa_por_anuncio']
    
    # Top usuarios por vistas
    pipeline = [
        {'$group': {
            '_id': '$usuario',
            'total_vistas': {'$sum': 1},
            'total_ganado': {'$sum': '$recompensa'}
        }},
        {'$sort': {'total_vistas': -1}},
        {'$limit': 10}
    ]
    
    top_usuarios = list(collections['anuncios_vistas'].aggregate(pipeline))
    
    # Vistas recientes
    vistas_recientes = list(collections['anuncios_vistas'].find().sort('fecha', -1).limit(20))
    
    return render_template('admin_anuncios.html',
                         total_vistas_hoy=total_vistas_hoy,
                         total_recompensas_hoy=round(total_recompensas_hoy, 2),
                         top_usuarios=top_usuarios,
                         vistas_recientes=vistas_recientes,
                         config=ANUNCIOS_CONFIG)

if __name__ == '__main__':
    app.run(debug=True)
