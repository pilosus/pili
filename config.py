#!/usr/bin/env python

import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 Mb
    SSL_DISABLE = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT') or 587
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    PILI_APP_NAME = 'Pili'
    PILI_MAIL_SUBJECT_PREFIX = '[{0}] '.format(PILI_APP_NAME)
    PILI_MAIL_SENDER = '{0} Mailer <{1}>'.format(PILI_APP_NAME, MAIL_USERNAME)
    PILI_ADMIN = os.environ.get('PILI_ADMIN') or 'samigullinv@gmail.com' # app admin email
    PILI_ADMIN_NAME = os.environ.get('PILI_ADMIN_NAME') or 'Administrator'
    PILI_POSTS_PER_PAGE = int(os.environ.get('PILI_POSTS_PER_PAGE', 10))
    PILI_CATEGORIES_PER_PAGE = int(os.environ.get('PILI_CATEGORIES_PER_PAGE', 10))
    PILI_TAGS_PER_PAGE = int(os.environ.get('PILI_TAGS_PER_PAGE', 100))
    PILI_IMAGES_PER_PAGE = int(os.environ.get('PILI_IMAGES_PER_PAGE', 10))
    PILI_COMMENTS_PER_PAGE = int(os.environ.get('PILI_COMMENTS_PER_PAGE', 10))
    PILI_USERS_PER_PAGE = int(os.environ.get('PILI_COMMENTS_PER_PAGE', 10))
    PILI_COMMENTS_SCREENING = True # comment screened by default
    PILI_FOLLOWERS_PER_PAGE = int(os.environ.get('PILI_FOLLOWERS_PER_PAGE', 100))
    PILI_SLOW_DB_QUERY_TIME = 0.5
    PILI_ROLES_EDIT_OTHERS_POSTS = ['Editor', 'Administrator']
    PILI_SHOW_ALL_FOLLOWED = ['index', 'tag', 'category']
    PILI_STATIC_DIR = os.path.join(basedir, 'app/static')
    PILI_UPLOADS = os.path.join(PILI_STATIC_DIR, 'uploads')
    PILI_ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'gif', 'png']
    ##  Flask-thumbnails settings
    MEDIA_FOLDER = PILI_UPLOADS
    MEDIA_URL = '/static/uploads/'
    MEDIA_THUMBNAIL_FOLDER = os.path.join(PILI_UPLOADS, 'thumbnails') # chmod 775
    MEDIA_THUMBNAIL_URL = '/static/uploads/thumbnails/'
    ## Allowed html tags and attributes
    PILI_ALLOWED_TAGS = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                         'em', 'i', 'img', 'li', 'ol', 'pre', 'strong', 'ul',
                         'h1', 'h2', 'h3', 'p', 'div', 'span']
    PILI_ALLOWED_ATTRIBUTES = {'*': ['class', 'id'],
                               'a': ['href', 'rel'],
                               'img': ['src', 'alt']}
    PILI_ALLOWED_COMMENT_TAGS = ['a', 'abbr', 'acronym', 'b', 'code', 'em',
                                 'i', 'strong']
    POST_TRUNCATE = {'length': 128, 'killwords': True, 'end': '...'}

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
            fromaddr=cls.PILI_MAIL_SENDER,
            toaddrs=[cls.PILI_ADMIN],
            subject=cls.PILI_MAIL_SUBJECT_PREFIX + ' Application Error',
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
