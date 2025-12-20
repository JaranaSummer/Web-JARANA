from flask_frozen import Freezer
from app import app

# Esto es vital para que GitHub Pages entienda las rutas
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['FREEZER_DESTINATION'] = 'docs'

freezer = Freezer(app)

if __name__ == '__main__':
    freezer.freeze()
    print("Web estática generada en /docs")