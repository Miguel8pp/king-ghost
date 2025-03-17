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

# Ruta principal
# Ruta principal
@app.route('/pagina_principal')
def pagina_principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
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

# Ruta para agregar una orden
@app.route('/agregar_orden', methods=['GET', 'POST'])
def agregar_orden():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    saldo = obtener_saldo(usuario)

    # Si el saldo es 0 o inferior, mostrar el mensaje de "Saldo Insuficiente"
    if saldo <= 0:
        flash("Saldo Insuficiente. No tienes saldo suficiente para realizar pedidos.", "error")
        
        # Antes de redirigir, asegurémonos de que 'categories' y 'services' son listas válidas
        api = Api()
        categories = api.categories()
        services = api.services()

        # Verificar los datos antes de limpiarlos
        print("Categorías originales:", categories)
        print("Servicios originales:", services)

        # Limpiar los valores None de categories y services
        categories = [category for category in categories if category is not None]
        services = [service for service in services if service is not None]

        # Verificar después de la limpieza
        print("Categorías después de limpieza:", categories)
        print("Servicios después de limpieza:", services)

        # Renderizar la plantilla sin hacer nada más si no hay saldo
        return render_template('yoursmm.html', usuario=usuario, saldo=saldo, categories=categories, services=services)

    api = Api()
    categories = api.categories()
    services = api.services()

    # Verificar los datos antes de limpiarlos
    print("Categorías originales (cuando hay saldo):", categories)
    print("Servicios originales (cuando hay saldo):", services)

    # Limpiar los valores None de categories y services
    categories = [category for category in categories if category is not None]
    services = [service for service in services if service is not None]

    # Verificar después de la limpieza
    print("Categorías después de limpieza (cuando hay saldo):", categories)
    print("Servicios después de limpieza (cuando hay saldo):", services)

    if request.method == 'POST':
        cantidad = int(request.form['quantity'])
        servicio_id = request.form['service']
        enlace = request.form['link']

        # Obtener el servicio correspondiente
        servicio = next((s for s in services if s['service'] == servicio_id), None)

        if servicio:
            precio_por_unidad = float(servicio.get('rate', 0)) * 1.40  # Aumento del 40%

            monto = (cantidad * precio_por_unidad) / 1000

            # Verificar si el saldo es suficiente para realizar el pedido
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
        user_data = collection.find_one({'usuario': session['usuario']})
        # Verificar el rol del usuario
        if user_data.get('rol') == 'admin':
            return redirect(url_for('admin_dashboard'))  # Redirigir al panel de administración si es admin
        return redirect(url_for('pagina_principal'))  # Redirigir a la página principal si es usuario normal

    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['contrasena']
        
        user_data = collection.find_one({'usuario': username})
        if user_data and bcrypt.check_password_hash(user_data['contrasena'], password):
            session['usuario'] = username
            # Verificar el rol del usuario y redirigir
            if user_data.get('rol') == 'admin':
                return redirect(url_for('admin_dashboard'))  # Redirigir a la vista de admin si es admin
            flash("Bienvenido de nuevo!", "success")
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
            'rol': 'user'
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
@app.route('/mi_perfil')
def mi_perfil():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    usuario = session['usuario']
    user_data = collection.find_one({'usuario': usuario})
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
def historial_pedidos():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    usuario = session['usuario']
    pedidos = pedidos_collection.find({'usuario': usuario})
    return render_template('pedidos.html', usuario=usuario, pedidos=pedidos)

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
        
        # Redirigir después de realizar la acción POST
        return redirect(url_for('admin_dashboard'))

    return render_template('admin.html', usuarios=usuarios)




# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
