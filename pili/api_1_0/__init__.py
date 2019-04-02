from flask import Blueprint

api = Blueprint('api', __name__)

from . import authentication, comments, errors, posts, tags, users, uploads, messages
