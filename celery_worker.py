#!/usr/bin/env python

"""
celery worker to be run as follows:

(venv) $ celery worker -A celery_worker.celery --loglevel=info
"""

import os
from app import celery, create_app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
app.app_context().push()
