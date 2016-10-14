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
from app import celery, create_app

# set environment variables used for app's config
from setenv import load_vars
load_vars()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
app.app_context().push()
