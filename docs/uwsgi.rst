========================
uWSGI application server
========================

-------------
Configuration
-------------

See uWSGI documentation Configuration_ section as well as DO tutorial_
for general configuraion information.

See uWSGI documentation Logging_ and Multithreading_ section for
deeper understanding of these topics.

.. _Configuration: https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html
.. _tutorial: https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-centos-7
.. _Logging: http://uwsgi-docs.readthedocs.io/en/latest/Logging.html
.. _Multithreading: http://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html?highlight=enable-threads


-----
Usage
-----

#. **Stop** uwsgi:
   ``kill -INT $( cat /path/to/uswgi-master.pid )`` or
   ``uwsgi --stop /path/to/uswgi-master.pid``
   See uwsgi config file for absolute path of the master PID file.
#. 
