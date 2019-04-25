from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from pili.app import create_app


def create_dispatcher(config_name: str) -> DispatcherMiddleware:
    """
    App factory for dispatcher middleware managing multiple WSGI apps
    """
    main_app = create_app(config_name=config_name)
    metrics_url = main_app.config.get('METRICS_URL', '/metrics')
    return DispatcherMiddleware(main_app, {metrics_url: make_wsgi_app()})
