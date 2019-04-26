import os

import pytest

from pili.app import create_app, db
from pili.models import Role


def pytest_make_parametrize_id(config, val, argname):
    """
    Prettify output for parametrized tests
    """
    if isinstance(val, dict):
        return '{}({})'.format(
            argname, ', '.join('{}={}'.format(k, v) for k, v in val.items())
        )


@pytest.fixture(scope='function', autouse=True)
def app(request):
    """
    Return Flask Application with testing settings
    """
    config_name = os.environ['PILI_CONFIG'] = 'testing'
    app = create_app(config_name=config_name)
    app_context = app.app_context()
    app_context.push()

    app.config['SERVER_NAME'] = 'localhost:8080'
    app.testing = True

    # WATCH OUT! DANGER OF DATABASE DAMAGE
    # This fixture creates DB tables before each test and DROP ALL tables at the end
    # Make sure to pass correct DB settings
    db.create_all()
    Role.insert_roles()

    yield app

    db.session.remove()
    db.drop_all()
    app_context.pop()


@pytest.fixture
def client(app):
    """
    Return Flask Testing Client
    """
    yield app.test_client()


@pytest.fixture(scope='function')
def db_session():
    """
    Return SQLAlchemy DB session
    """
    session = db.session
    with session.no_autoflush:
        yield session

    # Rollback and remove session on teardown allows save time on tables creation/drop
    session.rollback()
    session.remove()
