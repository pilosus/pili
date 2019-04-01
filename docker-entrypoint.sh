#!/bin/sh

echo "Initialize DB..."
python3.7 manage.py initialize

echo "Apply migrations to DB..."
python3.7 manage.py deploy

echo "Run server..."
python3.7 manage.py runserver --host=0.0.0.0
