from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail, celery

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['PILI_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['PILI_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


@celery.task
def send_celery_async_email(msg):
    mail.send(msg)

def send_celery_email(to, subject, template, countdown=None, **kwargs):
    """Send email async email using Celery.
    """
    app = current_app._get_current_object()
    msg = Message(app.config['PILI_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['PILI_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    send_celery_async_email.apply_async(args=[msg], countdown=countdown)
