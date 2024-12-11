from flask import Blueprint

auth_bp = Blueprint('auth', __name__, 
                   template_folder='templates',
                   static_folder='static',
                   static_url_path='/static')

def create_blueprint():
    from . import routes
    return auth_bp