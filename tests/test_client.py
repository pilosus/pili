import re
import time
from unittest.mock import patch

from pili.models import User


def test_home_page(app, client):
    with app.test_request_context():
        response = client.get('/')
        assert b'Stranger' in response.data


def test_register_login_logout(app, client):
    with patch('pili.app.request') as prometheus_mock, patch(
        'pili.auth.views.send_email'
    ) as email_mock:
        prometheus_mock._prometheus_metrics_request_start_time.return_value = (
            time.time()
        )
        email_mock.return_value = True

        # register a new account
        response = client.post(
            '/auth/register',
            data={
                'email': 'john@example.com',
                'username': 'john',
                'password': 'cat',
                'password2': 'cat',
            },
        )
        assert response.status_code == 302

        # login with the new account
        response = client.post(
            '/auth/login',
            data={'email': 'john@example.com', 'password': 'cat'},
            follow_redirects=True,
        )
        assert re.search(b'Hello,\s+john!', response.data)
        assert b'You have not confirmed your account yet' in response.data

        # send a confirmation token
        user = User.query.filter_by(email='john@example.com').first()
        token = user.generate_confirmation_token()
        response = client.get(
            '/auth/confirm/{token}'.format(token=token), follow_redirects=True
        )
        assert b'You have confirmed your account' in response.data

        # log out
        response = client.get('/auth/logout', follow_redirects=True)
        assert b'You have been logged out' in response.data
