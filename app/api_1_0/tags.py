from flask import jsonify, request, g, abort, url_for, current_app
from .. import db
from ..models import Post, Permission, Tag
from . import api
from .decorators import permission_required
from .errors import forbidden

@api.route('/tags/')
def get_tags():
    page = request.args.get('page', 1, type=int)
    pagination = Tag.query.paginate(
        page, per_page=current_app.config['FLASKY_TAGS_PER_PAGE'],
        error_out=False)
    tags = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_tags', page=page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_tags', page=page+1, _external=True)
    return jsonify({
        'tags': [tag.to_json() for tag in tags],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })

@api.route('/tags/titles.json')
def get_tags_list():
    """Return a list of tag titles."""
    tags = Tag.query.all()
    return jsonify({
        'tags': [tag.title for tag in tags]
    })

@api.route('/tags/<alias>')
def get_tag(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    return jsonify(tag.to_json())

@api.route('/tags/<alias>/posts/')
def get_tag_posts(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = tag.posts.order_by(Post.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page-1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=page+1, _external=True)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })
