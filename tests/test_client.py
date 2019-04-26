import re

from flask import url_for

from pili.models import User


def test_home_page(app, client):
    with app.test_request_context():
        response = client.get(url_for('main.index'))
        assert b'Stranger' in response.data


def test_register_login_logout(app, client):
    with app.test_request_context():
        # register a new account
        response = client.post(
            url_for('auth.register'),
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
            url_for('auth.login'),
            data={'email': 'john@example.com', 'password': 'cat'},
            follow_redirects=True,
        )
        assert re.search(b'Hello,\s+john!', response.data)
        assert b'You have not confirmed your account yet' in response.data

        # send a confirmation token
        user = User.query.filter_by(email='john@example.com').first()
        token = user.generate_confirmation_token()
        response = client.get(
            url_for('auth.confirm', token=token), follow_redirects=True
        )
        assert b'You have confirmed your account' in response.data

        # log out
        response = client.get(url_for('auth.logout'), follow_redirects=True)
        assert b'You have been logged out' in response.data
