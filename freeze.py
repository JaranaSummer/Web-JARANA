from flask_frozen import Freezer
from app import app

# Configuración para URLs limpias en GitHub Pages
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_DESTINATION'] = 'docs'

freezer = Freezer(app)

if __name__ == '__main__':
    print("Congelando web...")
    freezer.freeze()
    print("¡Listo! Los archivos están en /docs")