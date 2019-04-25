import os
import sys
import unittest
from typing import Any, Dict

import click
import flask_migrate
from werkzeug.serving import run_simple

from pili.app import create_app, db
from pili.entrypoints.dispatcher import create_dispatcher
from pili.models import Role, User

#
# Constants
#

CONFIG_OPTS = {'testing', 'development', 'production'}
UWSGI_OPTS = {'testing', 'development', 'production'}


#
# Helpers
#


def _validate_parameters(value, valid_values):
    if value not in valid_values:
        valid_options_str = ', '.join(valid_values)
        raise click.BadParameter('Option must be one of {}'.format(valid_options_str))
    return value


def _validate_config(ctx, param, value):
    """
    Validate configuration name passed to App's CLI
    """
    return _validate_parameters(value, CONFIG_OPTS)


def _validate_uwsgi(ctx, param, value):
    """
    Validate uWSGI section name passed to App's CLI
    """
    return _validate_parameters(value, UWSGI_OPTS)


#
# Tasks
#


@click.group()
@click.option(
    '--config',
    default='development',
    callback=_validate_config,
    help='Configuration name',
)
@click.pass_context
def cli(ctx: Any, config: str) -> None:
    """
    Pili App command line tool
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = config


@cli.command(help="Provision Application")
@click.option(
    '--db_init/--no-db_init',
    default=False,
    help='Initialize migration repository for DB',
)
@click.option(
    '--db_migrate/--no-db_migrate', default=False, help='Generate initial DB migration'
)
@click.option(
    '--db_upgrade/--no-db_upgrade', default=False, help='Apply migration to the DB'
)
@click.option(
    '--db_prepopulate/--no-db_prepopulate',
    default=False,
    help='Prepopulate DB with essential data',
)
@click.pass_context
def provision(
    ctx: Any, db_init: bool, db_migrate: bool, db_upgrade: bool, db_prepopulate: bool
) -> None:
    app = create_app(ctx.obj['config'])
    flask_migrate.Migrate(app=app, db=db)

    with app.app_context():
        if db_init:
            db.create_all()
            click.echo('---> Database tables created')

            flask_migrate.init()
            click.echo('---> Migration repository initialized')

        if db_migrate:
            flask_migrate.migrate()
            click.echo('---> Migration generated')

        if db_upgrade:
            flask_migrate.upgrade()
            click.echo('---> Migration applied')

        if db_prepopulate:
            Role.insert_roles()
            click.echo('---> Roles populated')

            User.add_admin()
            click.echo('---> Admin user created')

            User.add_self_follows()
            click.echo('---> Following configured')


@cli.command(help="Run Flask Development Server")
@click.option('--host', default='0.0.0.0', help='Flask Development Server Host')
@click.option('--port', default=8080, help='Flask Development Server Port')
@click.option(
    '--use_reloader/--no-use_reloader', default=True, help='Reload files on change'
)
@click.option(
    '--use_debugger/--no-use_debugger', default=False, help='Use werkzeug debugger'
)
@click.pass_context
def server(
    ctx: Any, host: str, port: int, use_reloader: bool, use_debugger: bool
) -> None:
    app = create_dispatcher(ctx.obj['config'])
    run_simple(
        hostname=host,
        port=port,
        application=app,
        use_reloader=use_reloader,
        use_debugger=use_debugger,
    )


@cli.command(help='Run uWSGI Application server')
@click.option(
    '--section',
    default='uwsgi',
    callback=_validate_uwsgi,
    help='uWSGI config file section name',
)
@click.pass_context
def uwsgi(ctx: Any, section: str) -> None:
    config_name = ctx.obj['config']
    os.system(
        'exec uwsgi --ini /app/etc/uwsgi.ini:{0} --pyargv "{1}"'.format(
            section, config_name
        )
    )


@cli.command(help="Run Python Shell")
@click.pass_context
def shell(ctx: Any) -> None:
    app = create_app(ctx.obj['config'])

    context: Dict[str, Any] = {}
    context.update(app.make_shell_context())

    banner = 'Python {0} on {1}\nApp: {2} [{3}]\nInstance: {4}'.format(
        sys.version, sys.platform, app.import_name, app.env, app.instance_path
    )
    try:
        from IPython import embed
        from traitlets.config import get_config

        config = get_config()
        config.InteractiveShellEmbed.colors = "Linux"
        embed(banner1=banner, config=config, **context)
    except ImportError:
        import code

        code.interact(banner=banner, local=context)


@cli.command(help="Run Tests")
@click.pass_context
def test(ctx: Any) -> None:
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    cli(obj={})
