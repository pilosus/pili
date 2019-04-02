from flask import abort, current_app, g, jsonify, request, url_for

from . import api
from .decorators import permission_required
from .errors import forbidden
from .. import db
from ..models import Permission, Post


@api.route('/messages/<int:id>')
def get_message(id):
    message = Message.query.get_or_404(id)
    return jsonify(message.to_json())
