import json

from flask import current_app, jsonify, request, url_for

from pili.api_1_0 import api
from pili.models import Category, Post, Upload


@api.route('/uploads/')
def get_uploads():
    page = request.args.get('page', 1, type=int)
    pagination = Upload.query.paginate(
        page, per_page=current_app.config['PILI_IMAGES_PER_PAGE'], error_out=False
    )
    uploads = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_uploads', page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for('api.get_uploads', page=page + 1, _external=True)
    return jsonify(
        {
            'uploads': [upload.to_json() for upload in uploads],
            'prev': prev,
            'next': next,
            'count': pagination.total,
        }
    )


# TODO
# Does URI conform to RESTful?
@api.route('/uploads/filenames.json')
def get_uploads_list():
    """Return a list of upload titles."""
    uploads = Upload.query.all()
    return jsonify({'uploads': [upload.filename for upload in uploads]})


@api.route('/uploads/filenames2.json')
def get_uploads_list2():
    """Return a list of upload titles."""
    uploads = Upload.query.all()
    # Considered unsafe
    return json.dumps([upload.filename for upload in uploads])


@api.route('/uploads/<filename>')
def get_upload(filename):
    upload = Upload.query.filter_by(filename=filename).first_or_404()
    return jsonify(upload.to_json())


@api.route('/uploads/<filename>/posts/')
def get_upload_posts(filename):
    upload = Upload.query.filter_by(filename=filename).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = upload.posts.order_by(Post.timestamp.asc()).paginate(
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


@api.route('/uploads/<filename>/categories/')
def get_upload_categories(filename):
    upload = Upload.query.filter_by(filename=filename).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = upload.categories.order_by(Category.timestamp.asc()).paginate(
        page, per_page=current_app.config['PILI_CATEGORIES_PER_PAGE'], error_out=False
    )
    categories = pagination.items
    prev = None
    if pagination.has_prev:
        # TODO
        # api.get_categories
        prev = url_for('api.get_posts', page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        # TODO
        # api.get_categories
        next = url_for('api.get_posts', page=page + 1, _external=True)
    return jsonify(
        {
            'categories': [category.to_json() for category in categories],
            'prev': prev,
            'next': next,
            'count': pagination.total,
        }
    )


# TODO
# upload image
# remove image
