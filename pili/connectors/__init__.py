import flask

from typing import Optional


class BaseConnector(object):
    def __init__(self, app: Optional[flask.Flask] = None) -> None:
        """
        Bind app to the object
        """
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: flask.Flask) -> None:
        """
        Do something with app instance already initialized with settings
        """
        app.teardown_appcontext(self.teardown)

    def bind_app(self, app: flask.Flask) -> None:
        """
        Bind connector to the app

        Used when current app should be passed to a connector
        """
        self.app = app
        self.init_app(app)

    def startup(self):
        """
        Do something to start connection
        """
        raise NotImplementedError()

    def teardown(self, exception):
        """
        Do something on app's context being popped , e.g. close connections
        """
        raise NotImplementedError()

    @property
    def connection(self):
        """
        Connector's entrypoint
        """
        context = flask._app_ctx_stack.top
        if context is not None:
            connector_name = self.__class__.__name__
            if not hasattr(context, connector_name):
                setattr(context, connector_name, self.startup())
            return getattr(context, connector_name)
