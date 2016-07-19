from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, CommentForm
from .. import db
from ..models import Permission, Role, User, Post, \
    Tag, Tagification, Comment, Reply, Category
from ..decorators import admin_required, permission_required
from ..filters import sanitize_alias, sanitize_tags, get_added_removed

@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    tags = Tag.query.all()
    categories = Category.query.all()
    return render_template('main/index.html', posts=posts, tags=tags,
                           categories=categories,
                           show_followed=show_followed, pagination=pagination)

@main.route('/tag/<alias>')
def tag(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    page = request.args.get('page', 1, type=int)

    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts.filter(Post.tags.contains(tag))
    else:
        query = tag.posts
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('main/tag.html', tag=tag, posts=posts,
                           show_followed=show_followed, pagination=pagination)

    
    pagination = tag.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)    
    posts = pagination.items
    return render_template('main/tag.html', tag=tag,
                           pagination=pagination, posts=posts)

@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
                           pagination=pagination)

@main.route('/<category>/<int:id>/<alias>', methods=['GET', 'POST'])
@main.route('/<category>/<int:id>/<alias>/reply/<int:parent_id>', methods=['GET', 'POST'])
def post(category, id, alias, parent_id=None):
    # https://stackoverflow.com/questions/17873820/flask-url-for-with-multiple-parameters
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if parent_id:
        parent_comment = Comment.query.get_or_404(parent_id)
        repliee = parent_comment.author
        # parent comment should be under the current post
        if parent_comment.post_id != id:
            flash('Operation is not permitted.', 'warning')
            return redirect(url_for('main.post', category=post.category.alias,
                                    id=post.id, alias=post.alias, page=-1))
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, \
                          post=post, \
                          author=current_user._get_current_object())
        db.session.add(comment)
        # comment form prepopulated through Reply
        if parent_id:
            ## http://stackoverflow.com/a/5083472/4241180 ##
            # to get auto-incremented primary key for the comment,
            # one needs to flush session first and then use comment.id
            db.session.flush()
            reply = Reply(id=comment.id,
                          parent_id=parent_id, \
                          replier=current_user._get_current_object(), \
                          repliee=repliee)
            db.session.add(reply)
            
        flash('Your comment has been published.', 'success')
        return redirect(url_for('main.post', category=post.category.id,
                                id=post.id, alias=post.alias, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['PILI_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['PILI_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    # if it's a reply, then prepopulate the form
    if parent_id:
        form.body.data = parent_comment.author.username + ', '
    return render_template('main/post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)

@main.route('/category/<alias>', methods=['GET'])
def category(alias):
    category = Category.query.filter_by(alias=alias).first_or_404()
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts.filter(Post.category == category)
    else:
        query = category.posts
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('main/category.html', category=category, posts=posts,
                           show_followed=show_followed, pagination=pagination)

@main.route('/category/<cat_alias>/tag/<tag_alias>', methods=['GET'])
def category_tag(cat_alias, tag_alias):
    category = Category.query.filter_by(alias=cat_alias).first_or_404()
    tag = Tag.query.filter_by(alias=tag_alias).first_or_404()
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts.filter(Post.category == category)
    else:
        query = category.posts
    pagination = query.filter(Post.tags.contains(tag))\
                      .order_by(Post.timestamp.desc()).paginate(
                          page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
                          error_out=False)
    posts = pagination.items
    return render_template('main/category_tag.html', category=category,
                           tag=tag, posts=posts, show_followed=show_followed,
                           pagination=pagination)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'warning')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.', 'warning')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    flash('You are now following {0}.'.format(username), 'success')
    return redirect(url_for('main.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'warning')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.', 'warning')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following {0} anymore.'.format(username), 'warning')
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'warning')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['PILI_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'warning')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['PILI_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)

@main.route('/comments-by/<username>')
def comments(username):
    # .fisrt_or_404() could be used also
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'warning')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.comments.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('main/comments.html', user=user, comments=comments,
                           pagination=pagination)

@main.route('/replies-to/<username>')
def replies(username):
    """List of comments written as a reply to the user.
    """
    ### Restrict viewing comments to a user to the user itself
    #if current_user.is_anonymous or not current_user.username == username:
    #    flash('You have no permission to see comments to the user.')
    #    return redirect(url_for('.index'))
    user = User.query.filter_by(username=username).first()
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.join(Reply, Comment.id == Reply.id).\
                 filter(Reply.repliee_id == user.id).\
                 order_by(Comment.timestamp.desc()).paginate(
                     page, per_page=current_app.config['PILI_COMMENTS_PER_PAGE'],
                     error_out=False)
    comments = pagination.items
    return render_template('main/replies.html', user=user, comments=comments,
                           pagination=pagination)


# TODO
@main.route('/comment/reply/<int:id>')
@login_required
@permission_required(Permission.COMMENT)
def comment_reply(id, repliee_id, post_id):
    """Reply to a comment.
    """
    comment = Comment.query.get_or_404(id)
    repliee = User.query.filter_by(id=repliee_id).get_or_404()
    post = Post.query.get_or_404(id)
    replier = current_user._get_current_object()
    
    db.session.add(comment)
    #return redirect(url_for('.post',
    #                        id=pass,
    #                        page=request.args.get('page', 1, type=int)))

@main.route('/all/<page>')
@main.route('/all/<page>/<alias>')
@login_required
def show_all(page=None, alias=None):
    if page not in current_app.config['PILI_SHOW_ALL_FOLLOWED']:
        page = 'index'
        alias = None
    resp = make_response(redirect(url_for('.' + page, alias=alias)))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp

@main.route('/followed/<page>')
@main.route('/followed/<page>/<alias>')
@login_required
def show_followed(page=None, alias=None):
    if page not in current_app.config['PILI_SHOW_ALL_FOLLOWED']:
        page = 'index'
        alias = None
    resp = make_response(redirect(url_for('.' + page, alias=alias)))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp

@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('main/moderate.html', comments=comments,
                           pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


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
        if query.duration >= current_app.config['PILI_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning('Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' \
                                       % (query.statement, query.parameters, query.duration,
                                          query.context))
    return response
