================================
systemd services: up and running
================================

*systemd* is an init system used both on the dev linux server (Arch
Linux) as well as on the production server (CentOS 7).

In order to daemonize uWSGI application server and Celery
initialization instructions for each daemon were proposed in a form of
systemd configuration files. These files with *.service* extension are
kelp under *conf* directory:

* conf/pili-celery.service
* conf/pili-uwsgi.service

------------
Installation
------------

Installation of a systemd's unit file requires following steps:

#. Go to systemd's directory dedicated for custom unit files
``$ cd /etc/systemd/system``
#. Create a symlink to a unit file:
``$ ln -s /var/www/pili/your.service your.service``
#. Reload systemd daemon:
``$ sudo systemctl daemon-reload``
#. Start your service with:
``$ sudo systemctl start your.service``
#. Make sure it's running:
``$ sudo systemctl status your.service``
#. If service has failed, take a look at systemd's logs:
``$ sudo journalctl -xe``
