from flask import Blueprint

auth = Blueprint('auth', __name__)

from pili.auth import views
