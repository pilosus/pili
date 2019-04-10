from flask import jsonify

from . import api
from ..models import Message


@api.route('/messages/<int:id>')
def get_message(id):
    message = Message.query.get_or_404(id)
    return jsonify(message.to_json())
