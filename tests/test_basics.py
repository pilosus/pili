from flask import current_app


def test_app_exist():
    assert current_app is not None


def test_app_is_in_testing_mode():
    assert current_app.config['TESTING'] is True
