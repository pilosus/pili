#!/usr/bin/env python

"""
Entry point of the application
"""

import os

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='pili/*')
    COV.start()

# set environment variables
if os.path.exists('.hosting.env'):
    print('Importing environment from .hosting.env...')
    for line in open('.hosting.env'):
        var = line.strip().split('=')
        # exclude commentsand badly formed strings
        if len(var) == 2 and not var[0].startswith('#'):
            os.environ[var[0]] = var[1]

from pili import create_app, db
from pili.models import User, Role, Permission, Follow, Post, Tag, \
    Comment, Tagification, Category, Structure, Upload, Follow, \
    Message, MessageAck, Like
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)

def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role,
                Permission=Permission, Post=Post, Tag=Tag,
                Comment=Comment, Follow=Follow,
                Tagification=Tagification, Category=Category,
                Structure=Structure, Upload=Upload, Message=Message,
                MessageAck=MessageAck, Like=Like)
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()

@manager.command
def initialize():
    """Create all databases, initialize migration scripts before deploying."""
    from flask_migrate import init
    db.create_all()
    init()
    
@manager.command
def deploy():
    """Run deployment tasks."""
    from flask_migrate import migrate, upgrade
    from pili.models import Role, User

    # generate an initial migration
    migrate()
    
    # migrate database to latest revision
    upgrade()

    # create user roles
    Role.insert_roles()

    # add admin
    User.add_admin()

    # add self-follows
    User.add_self_follows()

    
if __name__ == '__main__':
    manager.run()
