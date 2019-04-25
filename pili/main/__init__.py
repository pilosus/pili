from flask import Blueprint

main = Blueprint('main', __name__)

from pili.main import views, errors
from pili.models import Permission


@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
