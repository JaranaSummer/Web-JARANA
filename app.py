import os
from dotenv import load_dotenv 
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# Carga variables de entorno si existe el archivo .env (para local)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_dev_por_defecto') 

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CONFIGURACIÓN DE LA BASE DE DATOS (MODIFICADO) ---
# Intentamos obtener la URL de la base de datos de las variables de entorno (Render)
database_url = os.getenv('DATABASE_URL')

if database_url:
    # Estamos en Render (Producción)
    # Corrección: SQLAlchemy necesita que empiece con postgresql://, pero Render da postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # No hay variable, estamos en tu PC (Local)
    # Usamos SQLite como siempre
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# -------------------------------------------------------

os.makedirs(os.path.join(app.root_path, UPLOAD_FOLDER), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- MODELOS ---
class RRPP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    localidad = db.Column(db.String(100))
    nombre = db.Column(db.String(100))
    foto_filename = db.Column(db.String(500))
    foto_url = db.Column(db.String(500))      
    instagram = db.Column(db.String(200))
    whatsapp = db.Column(db.String(200))
    orden = db.Column(db.Integer, default=99) 
    visible = db.Column(db.Boolean, default=True)

class Transporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ciudad = db.Column(db.String(100))
    nombre_taxi = db.Column(db.String(100))
    dueno = db.Column(db.String(100))
    descripcion = db.Column(db.String(200))
    precio = db.Column(db.String(50))
    whatsapp = db.Column(db.String(200))
    orden = db.Column(db.Integer, default=99) 
    visible = db.Column(db.Boolean, default=True)

class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto_header = db.Column(db.String(200))
    texto_footer = db.Column(db.String(200))
    texto_actualizacion = db.Column(db.String(200))

# --- RUTAS ---

@app.route('/')
def index():
    # Nota: Si la DB está vacía, esto podría dar error si no hay configuración
    # Pero el bloque final 'with app.app_context()' se encarga de crearla.
    config = Configuracion.query.first()
    rrpps = RRPP.query.filter_by(visible=True).order_by(RRPP.orden.asc()).all()
    return render_template('index.html', rrpps=rrpps, config=config, page='rrpp')

@app.route('/transportes')
def transportes():
    config = Configuracion.query.first()
    
    # 1. Traemos TODOS los transportes ordenados por tu número de 'orden'
    transportes_all = Transporte.query.filter_by(visible=True).order_by(Transporte.orden.asc()).all()
    
    # 2. LOGICA INTELIGENTE: Creamos la lista de ciudades basándonos en el orden de los transportes.
    # La ciudad aparecerá tan pronto como aparezca su primer transporte en la lista.
    lista_ciudades = []
    ciudades_vistas = set()
    
    for t in transportes_all:
        # .strip() elimina espacios accidentales al principio o final del nombre de la ciudad
        nombre_ciudad = t.ciudad.strip() 
        if nombre_ciudad not in ciudades_vistas:
            lista_ciudades.append(nombre_ciudad)
            ciudades_vistas.add(nombre_ciudad)
            
    return render_template('transportes.html', ciudades=lista_ciudades, transportes=transportes_all, config=config, page='transporte')

@app.route('/login', methods=['GET', 'POST'])
def login():
    config = Configuracion.query.first()
    if request.method == 'POST':
        usuario_real = os.getenv('ADMIN_USER')
        password_real = os.getenv('ADMIN_PASS')
        
        # Ojo: Si no tienes ADMIN_USER en Render, esto podría fallar.
        # Asegúrate de agregar ADMIN_USER y ADMIN_PASS en las Environment Variables de Render también.
        if request.form['username'] == usuario_real and request.form['password'] == password_real:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Datos incorrectos')
    return render_template('login.html', config=config)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    config = Configuracion.query.first()
    
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        
        if tipo == 'config_textos':
            config.texto_actualizacion = request.form['texto_actualizacion']
            config.texto_footer = request.form['texto_footer']
            config.texto_header = request.form['texto_header']
            db.session.commit()
            return redirect(url_for('admin'))

        elif tipo == 'add_rrpp':
            file = request.files['foto']
            filename = ''
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Guarda localmente (se borrará en Render al reiniciar, pero sirve temporalmente)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            orden_val = request.form.get('orden')
            if not orden_val: orden_val = 99

            nuevo = RRPP(
                localidad=request.form['localidad'],
                nombre=request.form['nombre'],
                foto_filename=filename,
                foto_url=request.form.get('foto_url'),
                instagram=request.form['instagram'],
                whatsapp=request.form['whatsapp'],
                orden=int(orden_val)
            )
            db.session.add(nuevo)
        
        elif tipo == 'add_transporte':
            orden_val = request.form.get('orden')
            if not orden_val: orden_val = 99

            nuevo = Transporte(
                ciudad=request.form['ciudad'],
                nombre_taxi=request.form['nombre_taxi'],
                dueno=request.form['dueno'],
                descripcion=request.form['descripcion'],
                precio=request.form['precio'],
                whatsapp=request.form['whatsapp'],
                orden=int(orden_val)
            )
            db.session.add(nuevo)
            
        elif tipo == 'toggle':
            id_obj = request.form['id']
            tabla = request.form['tabla']
            if tabla == 'rrpp':
                obj = RRPP.query.get(id_obj)
                obj.visible = not obj.visible
            elif tabla == 'transporte':
                obj = Transporte.query.get(id_obj)
                obj.visible = not obj.visible

        elif tipo == 'delete':
            id_borrar = request.form['id']
            tabla = request.form['tabla']
            if tabla == 'rrpp':
                RRPP.query.filter_by(id=id_borrar).delete()
            elif tabla == 'transporte':
                Transporte.query.filter_by(id=id_borrar).delete()

        db.session.commit()
        return redirect(url_for('admin'))

    rrpps = RRPP.query.order_by(RRPP.orden.asc()).all()
    transportes = Transporte.query.order_by(Transporte.orden.asc()).all()
    return render_template('admin.html', rrpps=rrpps, transportes=transportes, config=config)

@app.route('/edit/rrpp/<int:id>', methods=['GET', 'POST'])
def edit_rrpp(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    rrpp = RRPP.query.get_or_404(id)
    if request.method == 'POST':
        rrpp.localidad = request.form['localidad']
        rrpp.nombre = request.form['nombre']
        rrpp.instagram = request.form['instagram']
        rrpp.whatsapp = request.form['whatsapp']
        rrpp.foto_url = request.form.get('foto_url')
        
        orden_val = request.form.get('orden')
        if orden_val: rrpp.orden = int(orden_val)

        file = request.files['foto']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            rrpp.foto_filename = filename
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_rrpp.html', rrpp=rrpp)

@app.route('/edit/transporte/<int:id>', methods=['GET', 'POST'])
def edit_transporte(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    t = Transporte.query.get_or_404(id)
    if request.method == 'POST':
        t.ciudad = request.form['ciudad']
        t.nombre_taxi = request.form['nombre_taxi']
        t.dueno = request.form['dueno']
        t.descripcion = request.form['descripcion']
        t.precio = request.form['precio']
        t.whatsapp = request.form['whatsapp']
        
        orden_val = request.form.get('orden')
        if orden_val: t.orden = int(orden_val)

        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_transporte.html', transporte=t)

# --- CREACIÓN DE TABLAS INICIAL ---
with app.app_context():
    db.create_all()
    # Si la tabla de configuración está vacía, creamos el registro inicial
    if not Configuracion.query.first():
        db.session.add(Configuracion(
            texto_header="JARANA", 
            texto_footer="JARANA © 2024",
            texto_actualizacion="ACTUALIZADO HASTA: --/--"
        ))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)