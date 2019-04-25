#!/usr/bin/env python

"""Celery worker to be run as follows:
(venv) $ celery worker -A pili.entrypoints.celery.celery --loglevel=info

Environment variables (such as MAIL_SERVER, MAIL_USERNAME, etc.)
should be set using export:

(venv) $ export MAIL_SERVER=smtp.youserver.com

'export' keyword in bash sets a variable to current shell and all
processes started from current shell.

If environmental variables are not set properly celery may raise
SMTPServerDisconnected('please run connect() first'), as email
settings are effectively absent.

"""

import os

from pili.app import celery, create_app  # noqa

app = create_app(config_name=os.getenv('PILI_CONFIG', 'development'))
app.app_context().push()
