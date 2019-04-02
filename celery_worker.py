#!/usr/bin/env python

"""Celery worker to be run as follows:
(venv) $ celery worker -A celery_worker.celery --loglevel=info

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
from pili import celery, create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
app.app_context().push()
