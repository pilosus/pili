#!/usr/bin/env python

import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'One, Two, Fredy is Coming for You'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 Mb
    SSL_DISABLE = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'mail.gandi.net'
    MAIL_PORT = os.environ.get('MAIL_PORT') or 587
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MMSE_APP_NAME = 'MMSE'
    MMSE_MAIL_SUBJECT_PREFIX = '[{0}] '.format(MMSE_APP_NAME)
    MMSE_MAIL_SENDER = '{0} Mailer <mailer@pilosus.org>'.format(MMSE_APP_NAME)
    MMSE_ADMIN = os.environ.get('MMSE_ADMIN') or 'samigullinv@gmail.com' # app admin email
    MMSE_ADMIN_NAME = os.environ.get('MMSE_ADMIN_NAME') or 'Administrator'
    MMSE_POSTS_PER_PAGE = os.environ.get('MMSE_POSTS_PER_PAGE') or 10
    MMSE_TAGS_PER_PAGE = os.environ.get('MMSE_TAGS_PER_PAGE') or 100
    MMSE_IMAGES_PER_PAGE = os.environ.get('MMSE_IMAGES_PER_PAGE') or 100
    MMSE_SLOW_DB_QUERY_TIME = 0.5
    MMSE_SHOW_ALL_FOLLOWED = ['index', 'tag']
    MMSE_STATIC_DIR = os.path.join(basedir, 'app/static')
    MMSE_UPLOADS = os.path.join(MMSE_STATIC_DIR, 'uploads')
    MMSE_ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'gif', 'png']
    ##  Flask-thumbnails settings
    MEDIA_FOLDER = MMSE_UPLOADS
    MEDIA_URL = '/static/uploads/'
    MEDIA_THUMBNAIL_FOLDER = os.path.join(MMSE_UPLOADS, 'thumbnails') # chmod 775
    MEDIA_THUMBNAIL_URL = '/static/uploads/thumbnails/'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.MMSE_MAIL_SENDER,
            toaddrs=[cls.MMSE_ADMIN],
            subject=cls.MMSE_MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


class HerokuConfig(ProductionConfig):
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

class UnixConfig(ProductionConfig):
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        ## log to syslog
        # write to /var/log/messages
        # can be configured to write to a separate log file
        # see docs
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)        
        
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'unix': UnixConfig,

    'default': DevelopmentConfig
}

# env var FLASK_CONFIG should be set to one of these options
