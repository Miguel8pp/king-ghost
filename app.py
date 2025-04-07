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
pagos_collection = db['Pagos']        

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

@app.route('/')
def inicios():
    return send_from_directory('templates', 'inicio.html')

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

    print(f"Categories cleaned: {categories}")  # Imprimir para depuración
    print(f"Services cleaned: {services}")  # Imprimir para depuración

    return render_template('index.html', usuario=session['usuario'], saldo=saldo, categories=categories, services=services)

# Ruta para crear orden de pago
@app.route('/saldo', methods=['GET', 'POST'])
def saldo():
    if 'usuario' not in session:
        return redirect(url_for('login'))  # Redirigir a login si no hay usuario en la sesión

    # Obtener el saldo del usuario
    usuario = session['usuario']
    saldo = obtener_saldo(usuario)

    if request.method == 'POST':
        # Aquí manejamos el pago
        monto = float(request.form['monto'])  # Monto a agregar
        metodo_pago = request.form['metodo_pago']  # Método de pago seleccionado (PayPal, Binance, etc.)

        # Guardar la orden de pago en la base de datos (colección Pagos)
        try:
            # Insertar el pago en la colección "Pagos"
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

    # Renderizar la plantilla de saldo con el saldo del usuario
    return render_template('saldo.html', usuario=usuario, saldo=saldo)

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
    
    # Obtener los movimientos de pagos del usuario desde la base de datos
    usuario = session['usuario']
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
    
    return render_template('mov.html', usuario=usuario, pagos=pagos)


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
                    print(f"Error al realizar el pedido: {e}")
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
                return redirect(url_for('admin_dashboard'))
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
 
# Ruta para mostrar el perfil del usuario
# Ruta para mostrar el perfil del usuario y manejar cambios
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
            
            # Validación de contraseñas
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
            current_email = request.form['current-email']
            new_email = request.form['new-email']
            current_password_email = request.form['current-password-email']
            
            # Verificar si la contraseña es correcta
            if not bcrypt.check_password_hash(user_data['contrasena'], current_password_email):
                flash("Contraseña incorrecta.", "error")
            else:
                # Comprobar si el nuevo correo ya está registrado
                if collection.find_one({'email': new_email}):
                    flash("Este correo electrónico ya está registrado.", "error")
                else:
                    collection.update_one({'usuario': usuario}, {'$set': {'email': new_email}})
                    flash("Correo electrónico cambiado con éxito.", "success")

        # Redirigir al perfil para evitar el reenvío del formulario
        return redirect(url_for('mi_perfil'))

    return render_template('mi_perfil.html', usuario=user_data['usuario'], email=user_data['email'])

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
        return redirect(url_for('login'))  # Redirige a la página de login si no está autenticado

    usuario = session['usuario']
    saldo = obtener_saldo(usuario)  # Obtener saldo del usuario

    # Traer todos los pedidos del usuario desde la base de datos
    pedidos = pedidos_collection.find({'usuario': usuario})

    api = Api()

    # Iterar sobre los pedidos para obtener y actualizar el estado de cada uno
    for pedido in pedidos:
        order_id = pedido.get('order_id')
        if order_id:
            try:
                # Obtener el estado más reciente del pedido desde la API
                estado_actual = api.get_order_status(order_id)
                if estado_actual and 'status' in estado_actual:
                    nuevo_estado = estado_actual['status'].capitalize()  # Asegurarse de que la primera letra esté en mayúscula
                    
                    # Si el estado ha cambiado, actualizamos en la base de datos
                    if pedido['estado'] != nuevo_estado:
                        pedidos_collection.update_one(
                            {'_id': pedido['_id']},
                            {'$set': {'estado': nuevo_estado}}
                        )
            except Exception as e:
                print(f"Error al obtener el estado del pedido {order_id}: {e}")
    
    # Recargar los pedidos con los estados actualizados
    pedidos = pedidos_collection.find({'usuario': usuario})

    return render_template('pedidos.html', usuario=usuario, saldo=saldo, pedidos=pedidos)

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

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
