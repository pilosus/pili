from flask import Flask, request
from flask.logging import default_handler
from flask_bootstrap import Bootstrap
from flask_bootstrap import WebCDN
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_pagedown import PageDown
from flask_thumbnails import Thumbnail
from flask_wtf.csrf import CSRFProtect, CSRFError
from config import config, Config
from celery import Celery
from inspect import getmembers, isfunction
from raven.contrib.flask import Sentry
from typing import Any
from functools import partial

from pili.connectors.redis import RedisConnector, cache, cache_flask_view, rate_limit
from pili.version import get_version

import pili.jinja_filters
import logging


def get_client_remote_addr(*args, **kwargs):
    """
    Get user's remote address from the Request
    """
    return request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get(
        'REMOTE_ADDR'
    )


# Initialize extensions
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()  # type: Any
pagedown = PageDown()
thumb = Thumbnail()
csrf = CSRFProtect()
celery = Celery(
    __name__, backend=Config.CELERY_RESULT_BACKEND, broker=Config.CELERY_BROKER_URL
)
sentry = Sentry()

redis = RedisConnector()
cache = partial(cache, connector=redis, key_func=get_client_remote_addr)
cache_flask_view = partial(
    cache_flask_view, connector=redis, key_func=get_client_remote_addr
)
rate_limit = partial(rate_limit, connector=redis, key_func=get_client_remote_addr)

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'


def register_extensions(app):
    """
    Register and update extensions and connectors
    """

    class Connectors:
        pass

    try:
        connectors = app.connectors
    except AttributeError:
        connectors = app.connectors = Connectors()

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)

    db.init_app(app)
    connectors.db = db

    login_manager.init_app(app)
    pagedown.init_app(app)
    thumb.init_app(app)
    csrf.init_app(app)
    celery.conf.update(app.config)

    # Sentry
    sentry_config = {
        'dsn': app.config['SENTRY_DSN'],
        'include_paths': ['pili'],
        'environment': app.config.get('ENVIRONMENT', 'test'),
        'release': get_version(),
    }
    app.config.update(SENTRY_CONFIG=sentry_config)
    sentry.init_app(app)
    connectors.sentry = sentry

    # Connectors
    redis.bind_app(app)
    connectors.redis = redis

    # Update jinja
    template_filters = {
        name: function
        for name, function in getmembers(jinja_filters)
        if isfunction(function)
    }
    app.jinja_env.filters.update(template_filters)

    # Specify jQuery version
    app.extensions['bootstrap']['cdns']['jquery'] = WebCDN(
        '//cdnjs.cloudflare.com/ajax/libs/jquery/2.1.1/'
    )

    # SSL support
    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask_sslify import SSLify

        sslify = SSLify(app)


def register_blueprints(app):
    """
    Register blueprints to the app
    """
    from .main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    from .ctrl import ctrl as ctrl_blueprint

    app.register_blueprint(ctrl_blueprint, url_prefix='/ctrl')

    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api_1_0 import api as api_1_0_blueprint

    app.register_blueprint(api_1_0_blueprint, url_prefix='/api/v1.0')


def configure_logging(app) -> None:
    """
    Configure app's logging
    """
    app.logger.removeHandler(default_handler)

    log_formatter = logging.Formatter(
        fmt=app.config['LOG_FMT'], datefmt=app.config['LOG_DATEFMT']
    )
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(app.config['LOG_LEVEL'])
    app.logger.addHandler(log_handler)


def create_app(config_name):
    app = Flask(__name__)

    # update config
    configuration = config[config_name]
    configuration.init_app(app)
    app.config.from_object(configuration)

    # configure logging
    configure_logging(app)

    # update extensions and connectors
    register_extensions(app)

    # register blueprints
    register_blueprints(app)

    return app
