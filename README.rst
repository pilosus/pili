########
Pili App
########

Pili is a Python Flask application with a strong inclination
for social network and blogging features.

.. contents:: Table of Contents

==========
About Pili
==========
	      
-----
Stack
-----

Application is based on **Flask**, a light-weight Python web framework
that gets use of Werkzeug toolkit and Jinja2 template engine. Although
Flask works fine with both Python 2 and 3, Pili App's written with
**Python 3** in focus.

Database-agnostic, application uses **SQLAlchemy** ORM, which enables
user to choose between DBMS ranging from a simple SQLite to an
enterprise solution of user's choice.

Asynchronous tasks (such as email sending) tackled with **Celery**
distributed task queue, which is to be used with a message broker
software of user's choice such as **Redis** or **RabbitMQ**.

--------
Features
--------

#. Users

   * Registration
   * Authentication
   * Resetting/changing password
   * Creating/changing profile

#. Roles

   * Each user assigned one of the 7 predefined roles
   * Each role has a set of permissions
      
#. Posts

   * Tagging
   * Categorization (sectioning, which is useful for websites)
   * File upload

#. Comments

   * Write/delete comments
   * Screen/unscreen comments (not seen by the non-moderator users, all new comments can be set screened by default)
   * Disable/enable comments (non-moderators that disable comment exists, but its content disabled by the moderator)
   * Replies to the comments (users see replies to their comments)

#. Following

   * Follow/Unfollow other users to customize a feed

#. Likes

    * Authenticated users with ``FOLLOW`` permission can like/unlike posts or comments

#. Notifications

   * Get notifications from platform administrators
   * See replies to your comments

#. REST API
   
-------
Credits
-------

Pili App could not be possible without Miguel Grinberg's `Flasky App`_
developed as an example project for his excellent `Flask Web
Development`_ book published by O'Reilly Media in 2014.

Application comes with 3rd party libraries preinstalled:

#. `Bootstrap 3 Datetimepicker`_
#. `Typeahead.js`_
#. `Bootstrap Tagsinput`_

These libraries are found under::

  app/static/js
  app/static/css

The libraries belong to their owners and should not be considered as a
part of the application.


==========
Deployment
==========

-----------------
Environment setup
-----------------

Application's deployment follows the same steps as any other large
Flask application.

Setting up environment basically means:

#. Installing dependencies (Python packages)
#. Editing application's configurations files
#. Exporting shell environment variables

List of dependencies is made up of several parts:

#. Common dependencies
#. Dependencies specific for the environment (built upon common
   dependencies):

   * Development
   * Production (Unix server)
   * Heroku

Dependencies lists are found under::
   
    requirements/

*virtualenv* can be used for creating a virtual environment in the
app's working directory in order to install aforementioned
dependencies::

    $ virtualenv --python=python3 venv

Then virtual environment can be activated/deactivated::

    $ source venv/bin/activate
    (venv) $ deactivate

Dependencies can be installed then using ``pip``::

  (venv) $ pip install -r requirements/unix[prod|dev|...].txt

-----------------
App's config file
-----------------

Application gets use of environment variables. The whole list of such
variables can be found in ``config.py``.

These environment variables are set using shell-specific commands,
such as ``export`` in ``bash`` or ``setenv`` in ``csh``::

    (venv) $ export VARIABLE=value
    
**IMPORTANT!** Application also relies on ``.hosting.env`` file that 
is to be created by the user in the app's working directory. File 
format is the following::

    ENVVARIABLE=value of the environment variable

``.hosting.env`` is mandatory for ``manage.py`` file. It can also be
used in production when writing ``systemd`` service files (with
``EnvironmentFile`` directive).

**IMPORTANT!** Although ``manage.py`` sets environment variables found
in ``.hosting.env`` users cannot rely on it when working with Celery
workers. In this case environment variables are to be set in Celery's
own configuration (production) or with the shell's ``export`` command
(development).

-------------------
Database deployment
-------------------

Application uses `Flask-Migrate`_ for database migrations with
Alembic. Database deployment is made up of the following steps:

#. Create all databases used by the application, create migration
   repository::

     (venv) $ python manage.py initialize

#. Generate an initial migration, apply it to the database, then
   insert roles and add application's administrator::

     (venv) $ python manage.py deploy


---------------
Run application
---------------    

Now that the application is configured, DB created and migration repo
is created, the last two steps are needed in order to get the
application running:

#. Start Celery workers with::

     (venv) $ celery worker -A celery_worker.celery --loglevel=info

#. Start development server::

     (venv) $ python manage.py runserver

#. Go to http://127.0.0.0:5000 and enjoy!


-------------------------------
When application models changed
-------------------------------

Every time the database models (``app/models.py``) change do the following::

  (venv) $ python manage.py db migrate [--message MESSAGE]
  (venv) $ emacs $( ls -1th migrations/versions/*.py | head -1 ) # check and edit migration
  (venv) $ python manage.py db upgrade
  
========================
Deployment in production
========================

------------------------------------
Reverse-proxy and Application server
------------------------------------

Flask's built-in server is not suitable for production. There are
quite a few `deployment options`_ for production environment, both
self-hosted and PaaS.

Being WSGI application, Flask requires WSGI application server (such
as **uWSGI** or **Gunicorn**), which usually works in conjunction with
a reserve-proxy server such as **Nginx** that serves static files and
manages requests. That takes the load off the application server and
guarantees better performance::

  Client request <-> Reverse-Proxy <-> Application Server (127.0.0.1:port OR socket)
      ^                   |
      └--- static files --┘

----------------------
Configuration examples
----------------------
      
There are configuration examples under::

  examples/

These examples include:

#. Celery systemd service file:

   * pili-celery.conf
   * pili-celery.service

#. Nginx configuration:

   * pili-nginx.conf

#. uWSGI systemd service file, uWSGI ini-config file:

   * pili-uwsgi.conf
   * pili-uwsgi.ini
   * pili-uwsgi.service

#. Git hooks for deployment from a repository:

   * post-receive (assumes /var/www/pili owned by ``git`` user, see
     also `Deployment with Git`_)

-----------     
Permissions
-----------

Aforementioned systemd service file examples get use of two directories::

  /var/log/pili
  /var/run/pili
  
The best way to create these directories is using the following systemd directives::

  PermissionsStartOnly=true # run ExecStartPre with root permissions
  ExecStartPre=-/usr/bin/mkdir -p /var/log/pili
  ExecStartPre=-/usr/bin/mkdir -p /var/run/pili

---------------------------
Using systemd service files
---------------------------

When tailored to your needs, provided systemd service files can be
used this way:

#. Go to systemd's directory for custom unit files::
     
     $ cd /etc/systemd/system
     
#. Create a symlink to a unit file::
     
     $ ln -s /var/www/pili/your.service your.service
     
#. Reload systemd daemon::
     
     $ sudo systemctl daemon-reload
     
#. Start your service with::
     
     $ sudo systemctl start your.service
     
#. Make sure it's running::
     
     $ sudo systemctl status your.service
     
#. If service has failed, take a look at systemd's logs::
     
     $ sudo journalctl -xe

=====
Usage
=====

--------------
Script options
--------------

In addition to providing an apllication entry point ``manage.py``
provides several other options to be used with ``(venv) $ python manage.py option`` command:

test                          Run unit-tests
test --coverage               Run unit-tests with the coverage statistics (report is generated under ``tmp/coverage`` directory)
profiler                      Start the application under the code profiler (25 slowest function included by default)
profiler --length=N           Include N slowest function in profiler report
profiler --profile-dir=DIR    Save profiler report in the file under DIR
initialize                    Create all databases, initialize migration scripts before deploying
deploy                        Run deployment tasks (to be run after ``initialize`` tasks are done)
db                            Perform database migrations
shell                         Run a Python shell inside Flask application context
runserver                     Run the Flask development server i.e. app.run()

------------------------------------
Running shell in application context
------------------------------------

For testing purposes it's recommended to run Python REPL inside
application context with the **Flask-Script** built-in ``shell``
command::

  (venv) $ python manage.py shell

Examples:

Look up a body of the comment with id 10::
  
    >>> Comment.query.filter(Comment.id==10).first().body

Get a list of users with the role 'Writer'::
  
    >>> [u for u in Role.query.filter(Role.name == 'Writer').first().users]

Get a list of comments to the post with id 111::
  
    >>> [c for c in Post.query.filter(Post.id == 111).first().comments]

Get a list of replies to the comment contining a word 'flask'::

    >>> [r for r in Comment.query.filter(Comment.body.like("%flask%")).first().replies]

Get a parent comment of the reply with id 29 (parent attribute exists due to backref='parent' in models)::
  
    >>> Comment.query.filter(Comment.id == 29).first().parent

Get all replies written by the user 'Pilosus' in descending order (sort by the time of publication)::

    >>> user = User.query.filter(User.username == 'Pilosus').first()
    >>> Comment.query.join(Reply, Comment.author_id == User.id).\
    ... filter(Comment.parent_id.isnot(None), User.id == user.id).\
    ... order_by(Comment.timestamp.desc()).all()
    >>>
    >>> # the same but more concise
    >>>
    >>> Comment.query.filter(Comment.parent_id.isnot(None), Comment.author == user).\
    ... order_by(Comment.timestamp.desc()).\
    ... all()

Get all replies to the comment with id 23::

    >>> Comment.query.get(23).replies

Get a thread of all replies to the certain comment::

    |- Comment 1
    |- Comment 2
    |    |- Comment 4
    |    |    |- Comment 6
    |    |    
    |    |- Comment 5
    |    
    |- Comment 3	 

    >>> # Use Depth-First Search algorithm for graphs,
    >>> #              implemented as a static method
    >>>
    >>> Comment.dfs(Comment.query.get(2), print)
    >>> <Comment 4>
    >>> <Comment 6>
    >>> <Comment 5>

    
Get all post likes by the user with ``id`` 1, exclude comment likes::

    >>> Like.query.filter(Like.user_id==1, Like.comment_id == None).all()
    >>> Like.query.filter((Like.user_id==1) & (Like.comment_id == None)).all()

Get information about 'users' table::
  
    >>> User.__table__.columns
    >>> User.__table__.foreign_keys
    >>> User.__table__.constraints
    >>> User.__table__.indexes

.. _Flasky App: https://github.com/miguelgrinberg/flasky
.. _Flask Web Development: http://shop.oreilly.com/product/0636920031116.do
.. _Bootstrap 3 Datetimepicker: https://eonasdan.github.io/bootstrap-datetimepicker/Options/
.. _Typeahead.js: https://twitter.github.io/typeahead.js/examples/
.. _Bootstrap Tagsinput: https://bootstrap-tagsinput.github.io/bootstrap-tagsinput/examples/
.. _deployment options: http://flask.pocoo.org/docs/0.11/deploying/
.. _Deployment with Git: https://www.digitalocean.com/community/tutorials/how-to-use-git-hooks-to-automate-development-and-deployment-tasks
.. _Flask-Migrate: https://flask-migrate.readthedocs.io/en/latest/
