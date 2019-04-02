from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response, jsonify
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, CommentForm
from ..ctrl.forms import CsrfTokenForm
from .. import db
from ..models import Permission, Role, User, Post, \
    Tag, Tagification, Comment, Category, Message, MessageAck, Like
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

@main.route('/user/<username>/profile')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('main/user.html', user=user, posts=posts,
                           pagination=pagination)

@main.route('/<category>/<int:id>/<alias>', methods=['GET', 'POST'])
@main.route('/<category>/<int:id>/<alias>/reply/<int:parent_id>', methods=['GET', 'POST'])
def post(category, id, alias, parent_id=None):
    # https://stackoverflow.com/questions/17873820/flask-url-for-with-multiple-parameters
    post = Post.query.get_or_404(id)
    form = CommentForm()
    recipient = None
    if parent_id:
        parent_comment = Comment.query.get_or_404(parent_id)
        recipient = parent_comment.author
        # parent comment should be under the current post
        if parent_comment.post_id != id:
            flash('Operation is not permitted.', 'warning')
            return redirect(url_for('main.post', category=post.category.alias,
                                    id=post.id, alias=post.alias, page=-1))
    if form.validate_on_submit():
        screened = current_app.config['PILI_COMMENTS_SCREENING']
        comment = Comment(body=form.body.data,
                          parent_id=parent_id,
                          post=post,
                          screened=screened,
                          author=current_user._get_current_object(),
                          recipient=recipient)
        db.session.add(comment)
        """
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
        """
            
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

# TODO: rewrite as API function
@main.route('/like', methods=['POST'])
@login_required
@permission_required(Permission.FOLLOW)
def like_item():
    try:
        post_id = request.json.get('post_id', None)
        comment_id = request.json.get('comment_id', None)
        user_id = request.json.get('user_id', None)
        action = request.json.get('action', None)
        csrf = request.json.get('csrf', None)
    except (KeyError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Function takes four parameters: '
                       'post or commend id; user id; action type; csrf token',
        })


@main.route('/likes/post/<int:id>/like')
@login_required
@permission_required(Permission.FOLLOW)
def like_post(id):
    post = Post.query.get_or_404(id)
    like = Like(post=post, user=current_user)
    db.session.add(like)
    return redirect(url_for('main.post', category=post.category.alias,
                            id=post.id, alias=post.alias))


@main.route('/likes/post/<int:id>/unlike')
@login_required
@permission_required(Permission.FOLLOW)
def unlike_post(id):
    post = Post.query.get_or_404(id)
    like = Like.query.filter((Like.user == current_user) &
                             (Like.post == post)).first_or_404()
    db.session.delete(like)
    return redirect(url_for('main.post', category=post.category.alias,
                            id=post.id, alias=post.alias))

@main.route('/likes/comment/<int:id>/like')
@login_required
@permission_required(Permission.FOLLOW)
def like_comment(id):
    comment = Comment.query.get_or_404(id)
    like = Like(comment=comment, user=current_user)
    db.session.add(like)
    return redirect(url_for('main.post', category=comment.post.category.alias,
                            id=comment.post.id, alias=comment.post.alias,
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))


@main.route('/likes/comment/<int:id>/unlike')
@login_required
@permission_required(Permission.FOLLOW)
def unlike_comment(id):
    comment = Comment.query.get_or_404(id)
    like = Like.query.filter((Like.user == current_user) &
                             (Like.comment == comment)).first_or_404()
    db.session.delete(like)
    return redirect(url_for('main.post', category=comment.post.category.alias,
                            id=comment.post.id, alias=comment.post.alias,
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))

@main.route('/replies-to/bulk', methods=['POST'])
@login_required
def replies_bulk():
    def replies_action(comments, action):
        msg = {'read': 'marked as read',
               'unread': 'marked as not read'
        }
        message = ''
        fail = ''
        count = 0
        for id in comments:
            comment = Comment.query.get_or_404(id)
            if current_user._get_current_object() == comment.recipient:
                if action == 'read':
                    comment.read = True
                elif action == 'unread':
                    comment.read = False
                # add more actions here
                db.session.add(comment)
                message += str(id) + ', '
                count += 1
            else:
                fail += str(id) + ', '
        message = message.rstrip(', ')
        fail = fail.rstrip(', ')
        status = 'success'
        if message:
            message = 'Comments: {message} have been {action}.'.\
                      format(message=message, action=msg[action])
        if fail:
            fail = 'Comments: {fail} failed. You are not a recipient of them.'.\
                      format(fail=fail, action=msg[action])
            status = 'warning'
        return "{message} {fail}".format(message=message, fail=fail), status

    try:
        csrf = request.json['csrf']
        comments = list(map(lambda x: int(x), request.json['comments']))
        action = request.json['action']
    except (KeyError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Function takes three parameters: '
                       'list of comments to be processed; csrf token; action',
        })
    message, status = replies_action(comments, action)
    return jsonify({
            'status': status,
            'message': message
    })

@main.route('/replies-to/unread/<int:id>')
@login_required
def reply_mark_unread(id):
    comment = Comment.query.get_or_404(id)
    if current_user._get_current_object() == comment.recipient:
        comment.read = False
        db.session.add(comment)
    else:
        flash('Operation is not permitted. You are not a recipient of the comment', 'warning')
    return redirect(url_for('.replies', username=current_user.username,
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))


@main.route('/replies-to/read/<int:id>')
@login_required
def reply_mark_read(id):
    comment = Comment.query.get_or_404(id)
    if current_user._get_current_object() == comment.recipient:
        comment.read = True
        db.session.add(comment)
    else:
        flash('Operation is not permitted. You are not a recipient of the comment', 'warning')
    return redirect(url_for('.replies', username=current_user.username,
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))

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


@main.route('/user/<username>/follow')
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


@main.route('/user/<username>/unfollow')
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


@main.route('/user/<username>/followers')
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
    return render_template('main/followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/user/<username>/following')
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
    return render_template('main/followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)

@main.route('/user/<username>/comments-by')
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

@main.route('/user/<username>/replies-to')
def replies(username):
    """List of comments written as a reply to the user.
    """
    ### Restrict viewing comments to a user to the user itself
    #if current_user.is_anonymous or not current_user.username == username:
    #    flash('You have no permission to see comments to the user.')
    #    return redirect(url_for('.index'))
    csrf_form = CsrfTokenForm()
    user = User.query.filter_by(username=username).first()
    page = request.args.get('page', 1, type=int)
    # .join(Reply, Comment.id == Reply.id).filter(Reply.repliee_id == user.id).
    pagination = Comment.query.\
                 filter(Comment.recipient_id == user.id).\
                 order_by(Comment.timestamp.desc()).paginate(
                     page, per_page=current_app.config['PILI_COMMENTS_PER_PAGE'],
                     error_out=False)
    comments = pagination.items
    return render_template('main/replies.html', user=user, comments=comments,
                           csrf_form=csrf_form,
                           pagination=pagination)

@main.route('/user/<username>/notifications')
@login_required
def notifications(username):
    """List of messages sent to to the user.
    """
    ### Restrict viewing messages to a user to the user itself
    if not current_user.username == username:
        flash('You have no permission to see notifications to the user.')
        return redirect(url_for('.index'))
    csrf_form = CsrfTokenForm()
    user = User.query.filter_by(username=username).first()
    page = request.args.get('page', 1, type=int)
    pagination = MessageAck.query.\
                 join(Message, Message.id == MessageAck.message_id).\
                 filter(MessageAck.recipient_id == user.id).\
                 order_by(Message.timestamp.desc()).paginate(
                     page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
                     error_out=False)
    messages = pagination.items
    return render_template('main/notifications.html', user=user,
                           messages=messages,
                           csrf_form=csrf_form,
                           pagination=pagination)

@main.route('/notifications/bulk', methods=['POST'])
@login_required
def notifications_bulk():
    def notifications_action(notifications, action):
        msg = {'read': 'marked as read',
               'unread': 'marked as not read',
               'remove': 'removed'
        }
        message = ''
        fail = ''
        count = 0
        for id in notifications:
            msg_ack = MessageAck.query.get_or_404(id)
            if current_user._get_current_object() == msg_ack.recipient:
                if action == 'read':
                    msg_ack.read = True
                    db.session.add(msg_ack)
                elif action == 'unread':
                    msg_ack.read = False
                    db.session.add(msg_ack)
                elif action == 'remove':
                    db.session.delete(msg_ack)
                message += str(id) + ', '
                count += 1
            else:
                fail += str(id) + ', '
        message = message.rstrip(', ')
        fail = fail.rstrip(', ')
        status = 'success'
        if message:
            message = 'Notifications: {message} have been {action}.'.\
                      format(message=message, action=msg[action])
        if fail:
            fail = 'Notifications: {fail} failed. You are not a recipient of them.'.\
                      format(fail=fail, action=msg[action])
            status = 'warning'
        return "{message} {fail}".format(message=message, fail=fail), status

    try:
        csrf = request.json['csrf']
        notifications = list(map(lambda x: int(x), request.json['notifications']))
        action = request.json['action']
    except (KeyError, TypeError):
        return jsonify({
            'status': 'danger',
            'message': 'Function takes three parameters: '
                       'list of notifications to be processed; csrf token; action',
        })
    message, status = notifications_action(notifications, action)
    return jsonify({
            'status': status,
            'message': message
    })


@main.route('/user/<username>/notification/<int:id>', methods=['GET', 'POST'])
@login_required
def notification(username, id):
    csrf_form = CsrfTokenForm()
    if not current_user.username == username or \
       not current_user.can(Permission.ADMINISTER):
        flash('You have no permission to see notifications to the user.')
        return redirect(url_for('.index'))
    user = User.query.filter_by(username=username).first_or_404()
    ack = MessageAck.query.get_or_404(id)
    return render_template('main/notification.html', messages=[ack],
                           user=user, csrf_form=csrf_form)



@main.route('/user/<username>/notifications/remove/<int:id>')
@login_required
def remove_notification(username, id):
    if not current_user.username == username or \
       not current_user.can(Permission.ADMINISTER):
        flash('You have no permission to remove a notifications addressed to the user.')
        return redirect(url_for('.index'))
    user = User.query.filter_by(username=username).first_or_404()
    ack = MessageAck.query.get_or_404(id)
    db.session.delete(ack)
    flash("Notification {0} has been removed.".format(id), 'success')
    return redirect(url_for('main.notifications', username=username))

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
