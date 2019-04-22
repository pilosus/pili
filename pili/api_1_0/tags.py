import json

from flask import current_app, jsonify, request, url_for

from pili.models import Post, Tag
from pili.api_1_0 import api


@api.route('/tags/')
def get_tags():
    page = request.args.get('page', 1, type=int)
    pagination = Tag.query.paginate(
        page, per_page=current_app.config['PILI_TAGS_PER_PAGE'], error_out=False
    )
    tags = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_tags', page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_tags', page=page + 1, _external=True)
    return jsonify(
        {
            'tags': [tag.to_json() for tag in tags],
            'prev': prev,
            'next': next,
            'count': pagination.total,
        }
    )


@api.route('/tags/titles.json')
def get_tags_list():
    """Return a list of tag titles."""
    tags = Tag.query.all()
    return jsonify({'tags': [tag.title for tag in tags]})


@api.route('/tags/titles2.json')
def get_tags_list2():
    """Return a list of tag titles."""
    tags = Tag.query.all()
    # Considered unsafe
    return json.dumps([tag.title for tag in tags])


@api.route('/tags/<alias>')
def get_tag(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    return jsonify(tag.to_json())


@api.route('/tags/<alias>/posts/')
def get_tag_posts(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = tag.posts.order_by(Post.timestamp.asc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'], error_out=False
    )
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=page + 1, _external=True)
    return jsonify(
        {
            'posts': [post.to_json() for post in posts],
            'prev': prev,
            'next': next,
            'count': pagination.total,
        }
    )
