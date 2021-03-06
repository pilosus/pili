import os
from collections import OrderedDict
from re import sub

from flask import current_app
from unidecode import unidecode
from wtforms import ValidationError


def unique(seq):
    """Return list of unique elements preserving original order."""
    return list(OrderedDict.fromkeys(seq))


def sanitize_alias(s):
    """Return a string containing only lowercase latin letters and minus signs.

    Input string is trimed, non-word characters to be removed,
    whitespace characters separating words are to be replaced with
    dashes.
    """
    alias = sub(r"\s+", "-", unidecode(s.strip()))
    return sub(r"[^\w-]+", '', alias).lower()


def sanitize_tags(s):
    """Return a list of unique non-empty strings stripped from whitespaces.

    Input is string of comma-separated tags.
    """
    result = [t.strip() for t in s.split(',') if t.strip()]
    return unique(result)


def sanitize_upload(s):
    """
    Return a string containing only lowercase latin letters, minus,
    underscrore signs and dots.

    Input string is trimed, non-word characters to be removed,
    whitespace characters separating words are to be replaced with
    dashes.

    """
    fn = sub(r"\s+", "-", unidecode(s.strip()))
    return sub(r"[^\w-_.]+", '', fn).lower()


def is_allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1] in current_app.config['PILI_ALLOWED_EXTENSIONS']
    )


def file_exists(form, field):
    if os.path.isfile(
        os.path.join(current_app.config['PILI_UPLOADS'], field.data.filename)
    ):
        raise ValidationError('File already exists.')


def get_added_removed(new, old):
    """Return a tuple of two list.

    First list contains items present in the new, but absent in the old (added).
    Second list contains items present in the old, but absent in the new (removed).
    """
    added = []
    removed = []

    for i in new:
        if i not in old:
            added.append(i)

    for i in old:
        if i not in new:
            removed.append(i)

    return added, removed


def find_thumbnail(filename):
    """Return a string containing regexp for thumbnail file.

    Regexp consists of filename without file extension and trailing
    underscore.

    Assume: secure_filename by Werkzeug rename uploads so that file
    extension is always present.

    """
    return '.'.join(filename.split('.')[:-1]) + '_'


def generate_password(length=10):
    """Generate rnadom password of the given length.
    """
    import random
    import string

    return ''.join(
        random.SystemRandom().choice(
            string.ascii_lowercase + string.ascii_uppercase + string.digits
        )
        for _ in range(length)
    )


def to_bool(s: str) -> bool:
    """Return bool converted from string.

    bool() from the standard library convert all non-empty strings to True.
    """
    return s.lower() in ['true', 't', 'y', 'yes'] if s is not None else False
