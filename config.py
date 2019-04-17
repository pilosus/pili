#!/usr/bin/env python

import os
from pili.filters import to_bool
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 Mb
    SSL_DISABLE = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MAIL
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT') or 587
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # CELERY
    CELERY_ACCEPT_CONTENT = ['json', 'pickle']
    CELERY_INSTEAD_THREADING = to_bool(os.environ.get('CELERY_INSTEAD_THREADING'))
    CELERY_TASK_SERIALIZER = os.environ.get('CELERY_TASK_SERIALIZER') or 'pickle'
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')

    # FLOWER
    FLOWER_PORT = os.environ.get('FLOWER_PORT') or 5678
    FLOWER_BROKER_API = os.environ.get('FLOWER_BROKER_API')
    FLOWER_BROKER = None if FLOWER_BROKER_API else CELERY_BROKER_URL

    # SENTRY
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

    # APP
    PILI_APP_LOCALE_DEFAULT = os.environ.get('PILI_APP_LOCALE_DEFAULT')
    PILI_FB_API_ID = os.environ.get('PILI_FB_API_ID')
    PILI_APP_NAME = 'Pili'
    PILI_APP_SITE_NAME = os.environ.get('PILI_APP_SITE_NAME')
    PILI_APP_TITLE = 'Pili CMS'
    PILI_APP_AUTHOR = 'Pili Inc.'
    PILI_APP_DESCRIPTION = "Yet another CMS based on Python Flask. It's lightweight, fast and customizable."
    
    PILI_MAIL_SUBJECT_PREFIX = '[{0}] '.format(PILI_APP_NAME)
    PILI_MAIL_SENDER = '{0} Mailer <{1}>'.format(PILI_APP_NAME, MAIL_USERNAME)
    PILI_ADMIN = os.environ.get('PILI_ADMIN') or 'samigullinv@gmail.com' # pili admin email
    PILI_ADMIN_NAME = os.environ.get('PILI_ADMIN_NAME') or 'Administrator'
    PILI_POSTS_PER_PAGE = int(os.environ.get('PILI_POSTS_PER_PAGE', 10))
    PILI_CATEGORIES_PER_PAGE = int(os.environ.get('PILI_CATEGORIES_PER_PAGE', 10))
    PILI_TAGS_PER_PAGE = int(os.environ.get('PILI_TAGS_PER_PAGE', 100))
    PILI_IMAGES_PER_PAGE = int(os.environ.get('PILI_IMAGES_PER_PAGE', 10))
    PILI_COMMENTS_PER_PAGE = int(os.environ.get('PILI_COMMENTS_PER_PAGE', 10))
    PILI_USERS_PER_PAGE = int(os.environ.get('PILI_COMMENTS_PER_PAGE', 10))
    PILI_COMMENTS_SCREENING = True    # comment screened by default
    PILI_REGISTRATION_OPEN = True    # can new user register by themselves? 
    PILI_FOLLOWERS_PER_PAGE = int(os.environ.get('PILI_FOLLOWERS_PER_PAGE', 100))
    PILI_SLOW_DB_QUERY_TIME = 0.5
    PILI_ROLES_EDIT_OTHERS_POSTS = ['Editor', 'Administrator']
    PILI_SHOW_ALL_FOLLOWED = ['index', 'tag', 'category']
    PILI_STATIC_DIR = os.path.join(basedir, 'pili/static')
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
    # Truncate text in a template
    PILI_BODY_TRUNCATE = {'length': 128, 'killwords': True, 'end': '...'}

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')

    @staticmethod
    def init_app(app):
        # log to stderr
        import logging
        from logging import StreamHandler

        file_handler = StreamHandler()
        file_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(file_handler)


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

        # handle proxy server headers
        from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)


class HerokuConfig(ProductionConfig):
    SSL_DISABLE = bool(os.environ.get('SSL_DISABLE'))

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

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
