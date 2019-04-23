from typing import Optional

from flask import Response, current_app, jsonify
from werkzeug.exceptions import MethodNotAllowed
from werkzeug.routing import RequestRedirect

from pili.api_1_0 import api
from pili.connectors.redis import RateLimitExceededError
from pili.exceptions import (
    ForbiddenError,
    RequestError,
    UnauthorizedError,
    ValidationError,
)

#
# Exceptions
#


def json_error_handler(exc: RequestError) -> Response:
    """
    Basic error handler with JSON response
    """
    if hasattr(exc, 'message'):
        message = exc.message
    else:
        message = 'Internal Server Error'

    if hasattr(exc, 'status_code'):
        status_code = exc.status_code
    else:
        status_code = 500

    if hasattr(exc, 'origin'):
        origin = exc.origin
    else:
        origin = None

    if hasattr(exc, 'extra') and exc.extra is not None:
        extra = exc.extra
    else:
        extra = {}

    sentry_disable = current_app.config.get('SENTRY_DISABLE', False)
    sentry_exclude = current_app.config.get('SENTRY_EXCLUDE_STATUS_CODES', [])

    # Log exception to Sentry
    if not sentry_disable and (status_code not in sentry_exclude):
        try:
            raise origin  # type: ignore
        except Exception:
            current_app.connectors.sentry.client.captureException()
            current_app.logger.exception(str(origin))

    response = jsonify(
        {'errors': {'message': message, 'status_code': status_code, **extra}}
    )
    response.status_code = status_code
    return response


def bad_request(exc: Optional[Exception]):
    error = RequestError(message='Bad Request', status_code=400, origin=exc)
    return json_error_handler(error)


def unauthorized(exc: Optional[Exception]):
    error = RequestError(message='Unauthorized', status_code=401, origin=exc)
    return json_error_handler(error)


def forbidden(exc: Optional[Exception]):
    error = RequestError(message='Forbidden', status_code=403, origin=exc)
    return json_error_handler(error)


def method_not_allowed(exc: Optional[Exception]):
    error = RequestError(message='Method Not Allowed', status_code=405, origin=exc)
    return json_error_handler(error)


def page_not_found(exc: Optional[Exception]):
    error = RequestError(message='Page Not Found', status_code=404, origin=exc)
    return json_error_handler(error)


def rate_limit_error(exc: Optional[Exception]):
    error = RequestError(message='Too Many Requests', status_code=429, origin=exc)
    return json_error_handler(error)


def generic_error(exc: Optional[Exception]):
    error = RequestError(message='Internal Server Error', status_code=500, origin=exc)
    return json_error_handler(error)


#
# Register error handlers for the blueprint
#

# TODO
# Routing / Page not found problems cannot be handled at the blueprint level
# Workaround:
# https://github.com/pallets/flask/issues/503

api.register_error_handler(ValidationError, bad_request)
api.register_error_handler(UnauthorizedError, unauthorized)
api.register_error_handler(ForbiddenError, forbidden)
api.register_error_handler(RequestRedirect, page_not_found)
api.register_error_handler(MethodNotAllowed, method_not_allowed)
api.register_error_handler(RateLimitExceededError, rate_limit_error)
api.register_error_handler(Exception, generic_error)
