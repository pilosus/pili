from flask import jsonify

from pili.api_1_0 import api
from pili.models import Message


@api.route('/messages/<int:id>')
def get_message(id):
    message = Message.query.get_or_404(id)
    return jsonify(message.to_json())
