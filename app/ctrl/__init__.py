from flask import Blueprint

ctrl = Blueprint('ctrl', __name__)

from . import views, errors
from ..models import Permission

@ctrl.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
