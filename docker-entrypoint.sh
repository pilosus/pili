#!/bin/bash

if [[ ${FLASK_INIT} -eq 1 ]]
then
    echo "Initialize DB..."
    python3.7 manage.py initialize
fi


if [[ ${FLASK_DEPLOY} -eq 1 ]]
then
    echo "Apply migrations to DB..."
    python3.7 manage.py deploy
fi


if [[ ${FLASK_CONFIG} = "development" ]]
then
    echo "Run Flask development server..."
    python3.7 manage.py runserver --host 0.0.0.0 --port 8080
elif [[ ${FLASK_CONFIG} = "testing" ]]
then
    echo "Run tests..."
    python3.7 manage.py test
else
    echo "Run uWSGI production server"
    uwsgi --ini /app/etc/uwsgi.ini:${FLASK_CONFIG}
fi
