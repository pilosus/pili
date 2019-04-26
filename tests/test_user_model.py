import time
from datetime import datetime

import pytest

from pili.models import AnonymousUser, Follow, Permission, User


def test_password_setter():
    u = User(password='cat')
    assert u.password_hash is not None


def test_no_password_getter():
    u = User(password='cat')
    with pytest.raises(AttributeError):
        u.password


def test_password_verification():
    u = User(password='cat')
    assert u.verify_password('cat')
    assert not u.verify_password('dog')


def test_password_salts_are_random():
    u = User(password='cat')
    u2 = User(password='cat')
    assert u.password_hash != u2.password_hash


def test_valid_confirmation_token(db_session):
    u = User(password='cat')
    db_session.add(u)
    db_session.commit()
    token = u.generate_confirmation_token()
    assert u.confirm(token)


def test_invalid_confirmation_token(db_session):
    u1 = User(password='cat')
    u2 = User(password='dog')
    db_session.add(u1)
    db_session.add(u2)
    db_session.commit()
    token = u1.generate_confirmation_token()
    assert not u2.confirm(token)


def test_expired_confirmation_token(db_session):
    u = User(password='cat')
    db_session.add(u)
    db_session.commit()
    token = u.generate_confirmation_token(1)
    time.sleep(2)
    assert not u.confirm(token)


def test_valid_reset_token(db_session):
    u = User(password='cat')
    db_session.add(u)
    db_session.commit()
    token = u.generate_reset_token()
    assert u.reset_password(token, 'dog')
    assert u.verify_password('dog')


def test_invalid_reset_token(db_session):
    u1 = User(password='cat')
    u2 = User(password='dog')
    db_session.add(u1)
    db_session.add(u2)
    db_session.commit()
    token = u1.generate_reset_token()
    assert u2.reset_password(token, 'horse') is False
    assert u2.verify_password('dog') is True


def test_valid_email_change_token(db_session):
    u = User(email='john@example.com', password='cat')
    db_session.add(u)
    db_session.commit()
    token = u.generate_email_change_token('susan@example.org')
    assert u.change_email(token)
    assert u.email == 'susan@example.org'


def test_invalid_email_change_token(db_session):
    u1 = User(email='john@example.com', password='cat')
    u2 = User(email='susan@example.org', password='dog')
    db_session.add(u1)
    db_session.add(u2)
    db_session.commit()
    token = u1.generate_email_change_token('david@example.net')
    assert not u2.change_email(token)
    assert u2.email == 'susan@example.org'


def test_duplicate_email_change_token(db_session):
    u1 = User(email='john@example.com', password='cat')
    u2 = User(email='susan@example.org', password='dog')
    db_session.add(u1)
    db_session.add(u2)
    db_session.commit()
    token = u2.generate_email_change_token('john@example.com')
    assert not u2.change_email(token)
    assert u2.email == 'susan@example.org'


def test_roles_and_permissions():
    u = User(email='john@example.com', password='cat')
    assert u.can(Permission.FOLLOW)
    assert u.can(Permission.COMMENT)
    assert not u.can(Permission.WRITE)
    assert not u.can(Permission.MODERATE)
    assert u.has_role('Reader')


def test_anonymous_user():
    u = AnonymousUser()
    assert not u.can(Permission.FOLLOW)


def test_timestamps(db_session):
    u = User(password='cat')
    db_session.add(u)
    db_session.commit()
    assert (datetime.utcnow() - u.member_since).total_seconds() < 3
    assert (datetime.utcnow() - u.last_seen).total_seconds() < 3


def test_ping(db_session):
    u = User(password='cat')
    db_session.add(u)
    db_session.commit()
    time.sleep(2)
    last_seen_before = u.last_seen
    u.ping()
    assert u.last_seen > last_seen_before


def test_gravatar(app):
    u = User(email='john@example.com', password='cat')
    with app.test_request_context('/'):
        gravatar = u.gravatar()
        gravatar_256 = u.gravatar(size=256)
        gravatar_pg = u.gravatar(rating='pg')
        gravatar_retro = u.gravatar(default='retro')
    with app.test_request_context('/', base_url='https://example.com'):
        gravatar_ssl = u.gravatar()
    assert (
        'http://www.gravatar.com/avatar/' + 'd4c74594d841139328695756648b6bd6'
        in gravatar
    )
    assert 's=256' in gravatar_256
    assert 'r=pg' in gravatar_pg
    assert 'd=retro' in gravatar_retro
    assert (
        'https://secure.gravatar.com/avatar/' + 'd4c74594d841139328695756648b6bd6'
        in gravatar_ssl
    )


def test_follows(db_session):
    u1 = User(email='john@example.com', password='cat')
    u2 = User(email='susan@example.org', password='dog')
    db_session.add(u1)
    db_session.add(u2)
    db_session.commit()

    assert not u1.is_following(u2)
    assert not u1.is_followed_by(u2)
    timestamp_before = datetime.utcnow()
    u1.follow(u2)
    db_session.add(u1)
    db_session.commit()
    timestamp_after = datetime.utcnow()

    assert u1.is_following(u2)
    assert not u1.is_followed_by(u2)
    assert u2.is_followed_by(u1)
    assert u1.followed.count() == 2
    assert u2.followers.count() == 2

    f = u1.followed.all()[-1]
    assert f.followed == u2
    assert timestamp_before <= f.timestamp <= timestamp_after

    f = u2.followers.all()[-1]
    assert f.follower == u1

    u1.unfollow(u2)
    db_session.add(u1)
    db_session.commit()
    assert u1.followed.count() == 1
    assert u2.followers.count() == 1
    assert Follow.query.count() == 2

    u2.follow(u1)
    db_session.add(u1)
    db_session.add(u2)
    db_session.commit()
    db_session.delete(u2)
    db_session.commit()
    assert Follow.query.count() == 1
