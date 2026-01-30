import os
import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv 
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_dev_por_defecto') 

# Configuración de Cloudinary
cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Corrección para SQLAlchemy 2.0+ en Render/Heroku
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback para local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELOS ---
class RRPP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    localidad = db.Column(db.String(100))
    nombre = db.Column(db.String(100))
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
    config = Configuracion.query.first()
    rrpps = RRPP.query.filter_by(visible=True).order_by(RRPP.orden.asc()).all()
    return render_template('index.html', rrpps=rrpps, config=config, page='rrpp')

@app.route('/transportes/')
def transportes():
    config = Configuracion.query.first()
    transportes_all = Transporte.query.filter_by(visible=True).order_by(Transporte.orden.asc()).all()
    lista_ciudades = []
    ciudades_vistas = set()
    for t in transportes_all:
        nombre_ciudad = t.ciudad.strip() 
        if nombre_ciudad not in ciudades_vistas:
            lista_ciudades.append(nombre_ciudad)
            ciudades_vistas.add(nombre_ciudad)
    return render_template('transportes.html', ciudades=lista_ciudades, transportes=transportes_all, config=config, page='transportes')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == os.getenv('ADMIN_USER') and request.form['password'] == os.getenv('ADMIN_PASS'):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        flash('Datos incorrectos')
    return render_template('login.html', config=Configuracion.query.first())

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    config = Configuracion.query.first()
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        
        if tipo == 'add_rrpp':
            foto_final_url = request.form.get('foto_url')
            file = request.files.get('foto')
            
            if file and file.filename != '':
                upload_result = cloudinary.uploader.upload(file)
                foto_final_url = upload_result['secure_url']

            nuevo = RRPP(
                localidad=request.form['localidad'],
                nombre=request.form['nombre'],
                foto_url=foto_final_url,
                instagram=request.form['instagram'],
                whatsapp=request.form['whatsapp'],
                orden=int(request.form.get('orden', 99))
            )
            db.session.add(nuevo)

        elif tipo == 'add_transporte':
            nuevo = Transporte(
                ciudad=request.form['ciudad'],
                nombre_taxi=request.form['nombre_taxi'],
                dueno=request.form['dueno'],
                descripcion=request.form['descripcion'],
                precio=request.form['precio'],
                whatsapp=request.form['whatsapp'],
                orden=int(request.form.get('orden', 99))
            )
            db.session.add(nuevo)
        
        elif tipo == 'toggle':
            obj = RRPP.query.get(request.form['id']) if request.form['tabla'] == 'rrpp' else Transporte.query.get(request.form['id'])
            if obj: obj.visible = not obj.visible

        elif tipo == 'delete':
            if request.form['tabla'] == 'rrpp': RRPP.query.filter_by(id=request.form['id']).delete()
            else: Transporte.query.filter_by(id=request.form['id']).delete()

        elif tipo == 'config_textos':
            if not config:
                config = Configuracion(texto_header="", texto_footer="", texto_actualizacion="")
                db.session.add(config)
            config.texto_actualizacion = request.form['texto_actualizacion']
            config.texto_footer = request.form['texto_footer']
            config.texto_header = request.form['texto_header']

        db.session.commit()
        return redirect(url_for('admin'))

    rrpps = RRPP.query.order_by(RRPP.orden.asc()).all()
    transportes = Transporte.query.order_by(Transporte.orden.asc()).all()
    return render_template('admin.html', rrpps=rrpps, transportes=transportes, config=config)

@app.route('/publicar', methods=['POST'])
def publicar():
    if not session.get('logged_in'): return redirect(url_for('login'))
    url = f"https://api.github.com/repos/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}/dispatches"
    headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}", "Accept": "application/vnd.github.v3+json"}
    res = requests.post(url, json={"event_type": "update_static_site"}, headers=headers)
    flash("🚀 ¡Publicación iniciada! En 1 minuto la web estará actualizada." if res.status_code == 204 else "Error al publicar")
    return redirect(url_for('admin'))

@app.route('/edit/rrpp/<int:id>', methods=['GET', 'POST'])
def edit_rrpp(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    rrpp = RRPP.query.get_or_404(id)
    if request.method == 'POST':
        rrpp.localidad = request.form['localidad']
        rrpp.nombre = request.form['nombre']
        rrpp.instagram = request.form['instagram']
        rrpp.whatsapp = request.form['whatsapp']
        rrpp.orden = int(request.form.get('orden', 99))
        
        file = request.files.get('foto')
        if file and file.filename != '':
            upload_result = cloudinary.uploader.upload(file)
            rrpp.foto_url = upload_result['secure_url']
        elif request.form.get('foto_url'):
            rrpp.foto_url = request.form.get('foto_url')

        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_rrpp.html', rrpp=rrpp)

@app.route('/edit/transporte/<int:id>', methods=['GET', 'POST'])
def edit_transporte(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    t = Transporte.query.get_or_404(id)
    if request.method == 'POST':
        t.ciudad, t.nombre_taxi, t.dueno, t.descripcion, t.precio, t.whatsapp = request.form['ciudad'], request.form['nombre_taxi'], request.form['dueno'], request.form['descripcion'], request.form['precio'], request.form['whatsapp']
        t.orden = int(request.form.get('orden', 99))
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_transporte.html', transporte=t)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Esto es vital para Render: escuchar en el puerto que ellos asignan
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)