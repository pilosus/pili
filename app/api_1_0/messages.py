from flask import jsonify, request, g, abort, url_for, current_app
from .. import db
from ..models import Post, Permission
from . import api
from .decorators import permission_required
from .errors import forbidden

@api.route('/messages/<int:id>')
def get_message(id):
    message = Message.query.get_or_404(id)
    return jsonify(message.to_json())
