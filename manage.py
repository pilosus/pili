#!/usr/bin/env python
import os
COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

## hosting deployment. set environment variables
if os.path.exists('.hosting.env'):
    print('Importing environment from .hosting.env...')
    for line in open('.hosting.env'):
        var = line.strip().split('=')
        # exclude commentsand badly formed strings
        if len(var) == 2 and not var[0].startswith('#'):
            os.environ[var[0]] = var[1]
    
from app import create_app, db
from app.models import User, Role, Permission, Reply, Follow, Post, Tag, \
    Comment, Tagification, Category, Structure, Upload
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role,
                Permission=Permission, Post=Post, Tag=Tag,
                Comment=Comment, 
                Tagification=Tagification, Category=Category,
                Structure=Structure, Upload=Upload)
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
    from flask.ext.migrate import init
    db.create_all()
    init()
    
@manager.command
def deploy():
    """Run deployment tasks."""
    from flask.ext.migrate import upgrade
    from app.models import Role, User

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
