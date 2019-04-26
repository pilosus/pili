import os
from unittest.mock import patch

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


@pytest.fixture(scope='module', autouse=True)
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
    # This fixture creates DB tables before each module run and DROP ALL tables at the end
    # Make sure to pass correct DB settings
    db.create_all()
    Role.insert_roles()

    yield app

    db.drop_all()
    app_context.pop()


@pytest.fixture
def client(app):
    """
    Return Flask Testing Client
    """
    yield app.test_client()


#
# Use nested transaction to rollback any explicit commits
#
# https://docs.sqlalchemy.org/en/13/orm/session_transaction.html#
# joining-a-session-into-an-external-transaction-such-as-for-test-suites
#


@pytest.fixture(scope='function', autouse=True)
def nested_transaction_rollback(request, app):
    """
    Rollback transactions to a savepoint after each test run

    Allows to avoid dropping/recreating tables each time
    """

    current_session = db.session

    # start the session in a SAVEPOINT
    current_session.begin_nested()

    with patch.object(db, 'session', current_session):
        # then each time that SAVEPOINT ends, reopen it
        @db.event.listens_for(db.session, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                # ensure that state is expired the way
                # session.commit() at the top level normally does
                # (optional step)
                db.session.expire_all()
                db.session.begin_nested()

        db.session.begin_nested()
        with db.session.no_autoflush:
            yield

        # Rollback and remove session on teardown allows save time on tables creation/drop
        db.session.rollback()
        db.session.remove()
