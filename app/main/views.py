from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm,\
    CommentForm
from .. import db
from ..models import Permission, Role, User, Post, \
    Tag, Tagification
from ..decorators import admin_required, permission_required
from ..filters import sanitize_alias, sanitize_tags, get_added_removed

@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index_main.html', posts=posts, pagination=pagination)

@main.route('/tag/<alias>')
def tag(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = tag.posts.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
        error_out=False)    
    posts = pagination.items
    return render_template('tag.html', tag=tag,
                           pagination=pagination, posts=posts)

@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
                           pagination=pagination)

@main.route('/post/<int:id>-<alias>', methods=['GET'])
def post(id, alias, parent_id=None):
    post = Post.query.get_or_404(id)
    return render_template('post.html', posts=[post], pagination=pagination)

# TODO
@main.route('/category/<int:id>-<alias>', methods=['GET'])
def category(id, alias, parent_id=None):
    category = Category.query.get_or_404(id)
    return render_template('category.html', categories=[category], pagination=pagination)


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'

@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['MMSE_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning('Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' \
                                       % (query.statement, query.parameters, query.duration,
                                          query.context))
    return response
