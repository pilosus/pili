.. image:: https://circleci.com/gh/pilosus/pili/tree/master.svg?style=svg
    :target: https://circleci.com/gh/pilosus/pili/tree/master

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

.. _k8s:

=========================================
Deployment with Kubernetes (experimental)
=========================================

See Kubernetes configs in ``etc/k8s/`` directory. Assume the following commands are run within that directory.


----
Helm
----

Install `Helm`_, a package manager for Kubernetes. It's used to set up Redis_, RabbitMQ_ and PostgreSQL_.

.. _Helm: https://helm.sh/docs/using_helm/#installing-helm


.. _Redis:

-----
Redis
-----

#. Create config file under ``etc/config/values.redis.dev.yaml``

#. Install `stable/redis <https://github.com/helm/charts/tree/master/stable/redis>`_ helm chart::

  # omit --name option or use SemVer for versioning
  # make sure to specify redis hosts correctly in application's config files and config maps:
  # <your-release-name>-redis-master
  # <your-release-name>-redis-slave
  helm install --name pili-redis stable/redis --values etc/config/values.redis.dev.yaml

.. _RabbitMQ:

--------
RabbitMQ
--------

#. Create config file under ``etc/config/values.rabbitmq.dev.yaml``

#. Install `stable/rabbitmq <https://github.com/helm/charts/tree/master/stable/rabbitmq>`_ helm chart::

  helm install --name pili-rabbitmq -f etc/config/values.rabbitmq.dev.yaml stable/rabbitmq


.. _PostgreSQL:

----------
PostgreSQL
----------

#. Apply ``PersistentVolume`` and ``PersistentVolumeClaim`` for persistent queue storage::

  kubectl apply -f etc/k8s/pv.postgresql.dev.yaml
  kubectl apply -f etc/k8s/pvc.postgresql.dev.yaml


#. Create config file under ``etc/config/values.postgresql.dev.yaml``

#. Install `stable/postgresql <https://github.com/helm/charts/tree/master/stable/postgresql>`_ helm chart::

  helm install --name pili-db -f etc/config/values.postgresql.dev.yaml stable/postgresql


.. _ConfigMap:

-------------
Configuration
-------------

#. Add environment variables as a ``ConfigMap``::

  kubectl create configmap pili-config --from-env-file=etc/config/k8s.env


#. Make sure config is added correctly::

  kubectl get configmap pili-config -o yaml
  kubectl describe configmap pili-config

#. Add private docker registry credentials as a ``Secret`` using local ``~/.docker/config.json``::

  kubectl create secret generic registry-credentials \
      --from-file=.dockerconfigjson=/home/vitaly/.docker/config.json \
      --type=kubernetes.io/dockerconfigjson

#. Make sure secret's added correctly::

  kubectl get secret registry-credentials --output="jsonpath={.data.\.dockerconfigjson}" | base64 --decode



------------------
Persistent storage
------------------

Development
-----------

#. Create a mount point in the cluster::

  minikube ssh
  sudo mkdir -p /mnt/data/uploads

#. Create ``PersistentVolume``::

  kubectl apply -f etc/k8s/pv.app.dev.yaml

#. Create ``PersistentVolumeClaim``::

  kubectl apply -f etc/k8s/pvc.app.dev.yaml

----------------
Pili backend app
----------------

#. Apply ``Deployment``::

  kubectl apply -f etc/k8s/deployment.app.dev.yaml

#. Make sure deployment's applied::

  kubectl get pods

#. Apply ``Service``::

  kubectl apply -f etc/k8s/service.app.dev.yaml

#. Make sure services has started:

  kubectl describe service pili
  minikube service pili


-------------
Nginx Ingress
-------------


Development
-----------

#. Enable `Ingress`_ addon on minikube::

  minikube addons enable ingress


#. Apply ``Ingress`` manifest::

  kubectl apply -f etc/k8s/ingress.app.dev.yaml


#. After a while get ingress IP-address::

  kubectl get ingress


#. Add IP-address to ``/etc/hosts``::

  172.17.0.15 pili.org

#. Go to `http://pili.org <http://pili.org>`_ check everything works as expected

.. _Ingress: https://kubernetes.io/docs/tasks/access-application-cluster/ingress-minikube/


========================
Kubernetes Cluster Setup
========================

-----------
Development
-----------

Helm
----

Helm is a package manager for Kubernetes. `Install helm <https://helm.sh/docs/using_helm/#installing-helm>`_,
initialize it with::

  helm init --history-max 200


Resource configuration in Minikube
----------------------------------

Minikube starts with 2 CPU, 2Gb RAM and 20GB disk by default. Although it's sufficient in the most cases,
sometimes more or less resources needed. You may start your local cluster with arguments (see more options with
``minijube start -h``::

  minikube start --cpus 4 --memory 4096 --disk-size 20g

To make config options permanent you may edit ``~/.minikube/config/config.json`` file or set the options
from minikube cli (see more with ``minikube config -h``)::

  minikube config set cpus 4
  minikube config set memory 4096
  minikube config set disk-size 20g

Virtual Machine Driver
----------------------

On GNU/Linux machine install `kvm2 driver`_ and use it as a VM driver::

  minikube config set vm-driver kvm2


Beware! In order to improve VM performance further optimizations for ``kvm`` may be needed,
e.g. **enabling huge pages**. See `KVM`_ article for more information.

.. _kvm2 driver: https://github.com/kubernetes/minikube/blob/master/docs/drivers.md#kvm2-driver
.. _KVM: https://wiki.archlinux.org/index.php/KVM


Monitoring in Minikube
----------------------

Running ``k8s`` with a bunch of bloodthirsty services may require a tool for `resource monitoring`_.
In case of ``minikube`` a `heapster`_ and `metrics-server`_ monitoring should be activated::

  # alternatively use minikube addons enable <addon-name>
  minikube config set heapster true
  minikube config set metrics-server true

.. _resource monitoring: https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/
.. _heapster: https://github.com/kubernetes/minikube/blob/master/docs/addons.md
.. _metrics-server: https://kubernetes.io/docs/tasks/debug-application-cluster/resource-metrics-pipeline/#metrics-server



.. _DockerDeployment:

======================
Deployment with Docker
======================

-----------------
Local development
-----------------

#. Install ``docker>=18.06`` and ``docker-compose>=1.23.0``
#. Set environment variable ``PILI_CONFIG=development`` (you can place it to ``.env`` file in the root directory of the project)
#. Create file ``/etc/env/development.env`` and save enviroment variables needed for the app, e.g.::

    FLASK_CONFIG=development
    FLASK_ENV=development
    FLASK_INIT=1  # initialize DB with python manage.py initialize
    FLASK_DEPLOY=1  # prepopulate DB with python manage.py deploy
    SECRET_KEY=your_key
    SSL_DISABLE=1  # you don't need this in localhost
    DATABASE_URL=postgresql://pili:pili@db/pili  # use DB as docker-compose service
    CELERY_INSTEAD_THREADING=True  # use celery cervice
    CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672/  # use RabbitMQ as celery's broker
    CELERY_RESULT_BACKEND=redis://redis:6379/10  # celery result backend
    FLOWER_PORT=5678  # monitoring tool for celery
    FLOWER_BROKER_API=http://guest:guest@rabbitmq:15672/api/
    MAIL_SERVER=your_smtp
    MAIL_PORT=587
    MAIL_USE_TLS=True
    MAIL_USERNAME=you@your@smtp
    MAIL_PASSWORD=your_password

#. Run services with ``docker-compose up``
#. Open service with ``browse http://localhost:8080``
#. Open celery monitoring with ``browse http://localhost:5678``


Use ``make`` for the routine operations like:

#. Start/stop docker services with ``make up`` and ``make down`` respectively
#. Run linters with ``make lint``
#. Run `mypy`_ static analysis tool with ``make mypy``
#. Format code with `black formatter`_

.. _black formatter: https://github.com/ambv/black
.. _mypy: http://mypy-lang.org/


----------
Production
----------

The project uses `Circle CI`_ for CI/CD. As its final step CI/CD pushes docker image to a private docker registry.
The image can be used then in ``docker run``, ``docker-compose`` or in a ``Kubernetes cluster``.

.. _Circle CI: https://circleci.com/


==========
Deployment
==========

This section considered deprecated, see DockerDeployment_ for the suggested deployment model.

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

This section considered deprecated, see DockerDeployment_ for the suggested deployment model.

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
