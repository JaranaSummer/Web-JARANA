import os
from dotenv import load_dotenv 
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') 

# CONFIGURACIÓN DE CARGA DE IMÁGENES
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# CONFIGURACIÓN BASE DE DATOS
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

os.makedirs(os.path.join(app.root_path, UPLOAD_FOLDER), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- MODELOS ---
class RRPP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    localidad = db.Column(db.String(100))
    nombre = db.Column(db.String(100))
    foto_filename = db.Column(db.String(500))
    instagram = db.Column(db.String(200))
    whatsapp = db.Column(db.String(200))
    visible = db.Column(db.Boolean, default=True)

class Transporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ciudad = db.Column(db.String(100))
    nombre_taxi = db.Column(db.String(100))
    dueno = db.Column(db.String(100))
    descripcion = db.Column(db.String(200))
    precio = db.Column(db.String(50))
    whatsapp = db.Column(db.String(200))
    visible = db.Column(db.Boolean, default=True)

class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto_header = db.Column(db.String(200))
    texto_footer = db.Column(db.String(200))
    # NUEVO CAMPO:
    texto_actualizacion = db.Column(db.String(200))

# --- RUTAS ---

@app.route('/')
def index():
    config = Configuracion.query.first()
    rrpps = RRPP.query.filter_by(visible=True).all()
    return render_template('index.html', rrpps=rrpps, config=config, page='rrpp')

@app.route('/transportes')
def transportes():
    config = Configuracion.query.first()
    ciudades = db.session.query(Transporte.ciudad).distinct().all()
    lista_ciudades = [c[0] for c in ciudades]
    transportes_all = Transporte.query.filter_by(visible=True).all()
    return render_template('transportes.html', ciudades=lista_ciudades, transportes=transportes_all, config=config, page='transporte')

@app.route('/login', methods=['GET', 'POST'])
def login():
    config = Configuracion.query.first()
    if request.method == 'POST':
        # AQUÍ ESTÁ EL CAMBIO DE SEGURIDAD:
        # Le pedimos al sistema operativo (os) que busque las variables definidas en .env
        usuario_real = os.getenv('ADMIN_USER')
        password_real = os.getenv('ADMIN_PASS')
        
        # Comparamos lo que escribió el usuario con lo que está en el archivo secreto
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
        
        # --- NUEVA LÓGICA: ACTUALIZAR TEXTOS ---
        if tipo == 'config_textos':
            config.texto_actualizacion = request.form['texto_actualizacion']
            config.texto_footer = request.form['texto_footer']
            config.texto_header = request.form['texto_header']
            db.session.commit()
            return redirect(url_for('admin'))

        # AGREGAR RRPP
        elif tipo == 'add_rrpp':
            file = request.files['foto']
            filename = ''
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            nuevo = RRPP(
                localidad=request.form['localidad'],
                nombre=request.form['nombre'],
                foto_filename=filename,
                instagram=request.form['instagram'],
                whatsapp=request.form['whatsapp']
            )
            db.session.add(nuevo)
        
        # AGREGAR TRANSPORTE
        elif tipo == 'add_transporte':
            nuevo = Transporte(
                ciudad=request.form['ciudad'],
                nombre_taxi=request.form['nombre_taxi'],
                dueno=request.form['dueno'],
                descripcion=request.form['descripcion'],
                precio=request.form['precio'],
                whatsapp=request.form['whatsapp']
            )
            db.session.add(nuevo)
            
        # TOGGLE VISIBILIDAD
        elif tipo == 'toggle':
            id_obj = request.form['id']
            tabla = request.form['tabla']
            if tabla == 'rrpp':
                obj = RRPP.query.get(id_obj)
                obj.visible = not obj.visible
            elif tabla == 'transporte':
                obj = Transporte.query.get(id_obj)
                obj.visible = not obj.visible

        # ELIMINAR
        elif tipo == 'delete':
            id_borrar = request.form['id']
            tabla = request.form['tabla']
            if tabla == 'rrpp':
                RRPP.query.filter_by(id=id_borrar).delete()
            elif tabla == 'transporte':
                Transporte.query.filter_by(id=id_borrar).delete()

        db.session.commit()
        return redirect(url_for('admin'))

    rrpps = RRPP.query.all()
    transportes = Transporte.query.all()
    return render_template('admin.html', rrpps=rrpps, transportes=transportes, config=config)

# --- RUTAS EDICIÓN ---
@app.route('/edit/rrpp/<int:id>', methods=['GET', 'POST'])
def edit_rrpp(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    rrpp = RRPP.query.get_or_404(id)
    if request.method == 'POST':
        rrpp.localidad = request.form['localidad']
        rrpp.nombre = request.form['nombre']
        rrpp.instagram = request.form['instagram']
        rrpp.whatsapp = request.form['whatsapp']
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
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_transporte.html', transporte=t)

# --- INIT ---
with app.app_context():
    db.create_all()
    if not Configuracion.query.first():
        # Valores por defecto al crear la DB
        db.session.add(Configuracion(
            texto_header="JARANA", 
            texto_footer="JARANA © 2024 - Todos los derechos reservados",
            texto_actualizacion="ACTUALIZADO HASTA: --/--"
        ))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)