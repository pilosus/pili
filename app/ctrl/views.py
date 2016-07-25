from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response, send_from_directory, jsonify
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import ctrl
from .. import csrf
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, UploadForm, \
    CategoryForm, EditCategoryForm, RemoveEntryForm
from .. import db
from ..models import Permission, Role, User, Post, \
    Comment, Tag, Tagification, Category, Upload
from ..decorators import admin_required, permission_required
from ..filters import sanitize_alias, sanitize_tags, sanitize_upload, \
    get_added_removed, is_allowed_file, find_thumbnail
from werkzeug import secure_filename
from datetime import datetime
import os

@ctrl.route('/', methods=['GET', 'POST'])
def posts():
    remove_form = RemoveEntryForm()
    form = PostForm()
    if current_user.can(Permission.WRITE) and \
       form.validate_on_submit():
        ## add post
        upload = Upload.query.filter_by(filename=form.image.data).first()
        category = Category.query.filter_by(id=form.category.data).first()
        post = Post(title=form.title.data,
                    alias=sanitize_alias(form.alias.data),
                    timestamp=form.timestamp.data,
                    body=form.body.data,
                    author=current_user._get_current_object(),
                    image=upload,
                    featured=form.featured.data,
                    commenting=form.commenting.data,
                    category=category)
        db.session.add(post)
        
        ## add tags
        tags = sanitize_tags(form.tags.data)
        if tags:
            tag_aliases = [sanitize_alias(t) for t in tags]
            for t in zip(tags, tag_aliases):
                tag_title = t[0]
                tag_alias = t[1]
                tag = Tag.query.filter(Tag.alias == tag_alias).first()
                # add a single tag if it doesn't exist yet
                if not tag:
                    tag = Tag(title=tag_title, alias=tag_alias)
                    db.session.add(tag)
                
                # flush session to obtain post.id and tag.id
                db.session.flush()
                tagification = Tagification.query.filter_by\
                               (tag_id=tag.id, post_id=post.id).first()
                # add entry to M-to-M posts-tags table
                if not tagification:
                    cl = Tagification(tag_id=tag.id, post_id=post.id)
                    db.session.add(cl)

        flash('Your post has been published.', 'success')
        return redirect(url_for('.posts'))
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    post_truncate = current_app.config['POST_TRUNCATE']
    return render_template('ctrl/posts.html', remove_form=remove_form,
                           form=form, posts=posts,
                           post_truncate=post_truncate,
                           datetimepicker=datetime.utcnow(),
                           pagination=pagination)

# TODO
@ctrl.route('/remove-post', methods=['POST'])
def remove_post():
    try:
        id = request.json['id']
        csrf = request.json['csrf']
    except (KeyError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Function takes two parameters: '
                       'id of the entry to be removed; csrf token',
        })
        
    post = Post.query.get_or_404(id)
    # check permissions
    if current_user != post.author and \
       not (current_user.has_role('Administrator') or \
            current_user.has_role('Editor')):
        abort(403)
    # remove tags
    if post.tags.count():
        tags = post.tags.all()
        for t in tags:
            # remove entries from M2M tagification table 
            Tagification.query.filter_by(tag_id=t.id, post_id=post.id).\
                delete(synchronize_session='fetch')
            # if the tag is not in use in other post(s), remove it
            in_other_posts = Tagification.query.\
                             filter(Tagification.tag_id == t.id,
                                    Tagification.post_id != post.id).count()
            if not in_other_posts:
                db.session.delete(t)

    # TODO: remove comments
    status = 'success'
    message = "Post '{0}' has been removed".\
              format(post.title)
    db.session.delete(post)
    return jsonify({
        'status': status,
        'message': message,
    })

@ctrl.route('/tag/<alias>')
def tag(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = tag.posts.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)    
    posts = pagination.items
    return render_template('tag.html', tag=tag,
                           pagination=pagination, posts=posts)

@ctrl.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
                           pagination=pagination)


@ctrl.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@ctrl.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.', 'success')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@ctrl.route('/edit-post/<int:id>/<alias>', methods=['GET', 'POST'])
@login_required
def edit_post(id, alias):
    """Edit an existing post.
    
    User has to be logged in and be either:
    - Author of the post
    - Editor (role)
    - Administrator (role)
    """
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not (current_user.has_role('Administrator') or \
                 current_user.has_role('Editor')):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        upload = Upload.query.filter_by(filename=form.image.data).first()
        category = Category.query.filter_by(id=form.category.data).first()

        post.title = form.title.data
        post.alias = sanitize_alias(form.alias.data)
        post.timestamp = form.timestamp.data
        post.body = form.body.data
        post.image = upload
        post.featured = form.featured.data
        post.commenting = form.commenting.data
        post.category = category

        db.session.add(post)

        ### update tags
        new_tags = sanitize_tags(form.tags.data)
        old_tags = sanitize_tags(
            ', '.join([c.title for c in post.tags.all()]))
        added_tag_titles, removed_tag_titles = get_added_removed(
            new_tags,
            old_tags)
        ## add new tags
        added_tag_aliases = [sanitize_alias(c) for c in added_tag_titles]
        for c in zip(added_tag_titles, added_tag_aliases):
            tag_title = c[0]
            tag_alias = c[1]
            tag = Tag.query.filter(Tag.alias == \
                                             tag_alias).first()
            # if tag doesn't exist in the db, add it
            if not tag:
                tag = Tag(title=c[0], alias=c[1])
                db.session.add(tag)

            # add relation between the Post and the Tag
            # flush session to obtain tag.id, if the tag has been added recently
            db.session.flush()

            cl = Tagification(tag_id=tag.id, post_id=id)
            db.session.add(cl)
        
        ### remove obsolete tags
        removed_tag_aliases = [sanitize_alias(c) for c in removed_tag_titles]

        
        for c in zip(removed_tag_titles, removed_tag_aliases):
            tag_title = c[0]
            tag_alias = c[1]
            tag = Tag.query.filter(Tag.alias == \
                                             tag_alias).first()

            ## remove relations
            old_cl = Tagification.query.filter(Tagification.tag_id == \
                                                 tag.id, \
                                                 Tagification.post_id == id).first()
            db.session.delete(old_cl)

            ## remove tag, if it's not used in other posts
            other_cl = Tagification.query.filter(Tagification.tag_id == \
                                                   tag.id, \
                                                   Tagification.post_id != id).first()
            if not other_cl:
                db.session.delete(tag)
        
        flash('The post has been updated.', 'success')
        return redirect(url_for('main.post', category=post.category.alias,
                                id=post.id, alias=post.alias))
    form.title.data = post.title
    form.alias.data = post.alias
    form.timestamp.data = post.timestamp
    form.body.data = post.body
    if post.image:
        form.image.data = category.image.filename
    
    form.featured.data = post.featured
    form.commenting.data = post.commenting
    form.category.data = post.category
    form.tags.data =', '.join([c.title for c in post.tags.all()])
    return render_template('ctrl/edit_post.html', form=form,
                           datetimepicker=datetime.utcnow())

@ctrl.route('/edit-category/<alias>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.STRUCTURE)
def edit_category(alias):
    """Edit an existing category.
    """
    category = Category.query.filter_by(alias=alias).first_or_404()
    
    form = EditCategoryForm()
    if form.validate_on_submit():
        upload = Upload.query.filter_by(filename=form.image.data).first()

        category.title = form.title.data
        category.alias = form.alias.data
        category.body = form.body.data
        category.image = upload
        category.featured = form.featured.data
        category.timestamp = form.timestamp.data

        db.session.add(category)
        flash("Category '{0}' has been successfully updated.".\
              format(category.title), 'success')
        return redirect(url_for('main.category', alias=category.alias))
    # Render prefilled form
    form.title.data = category.title
    form.alias.data = category.alias
    form.body.data = category.body
    if category.image:
        form.image.data = category.image.filename
    form.featured.data = category.featured
    form.timestamp.data = category.timestamp

    return render_template('ctrl/edit_category.html', form=form,
                           datetimepicker=datetime.utcnow())



@ctrl.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'

@ctrl.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['PILI_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning('Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' \
                                       % (query.statement, query.parameters, query.duration,
                                          query.context))
    return response

@ctrl.route('/categories', methods=['GET', 'POST'])
@permission_required(Permission.STRUCTURE)
def categories():
    """Render a form to submit new category and a list of existing categories."""
    remove_form = RemoveEntryForm()
    form = CategoryForm()

    # create new category
    if form.validate_on_submit():
        upload = Upload.query.filter_by(filename=form.image.data).first()
        category = Category(author=current_user._get_current_object(),
                            title=form.title.data,
                            alias=sanitize_alias(form.alias.data),
                            body=form.body.data,
                            image=upload,
                            featured=form.featured.data,
                            timestamp=form.timestamp.data)
        db.session.add(category)
        flash("Category has been successfully created.", 'success')
        return redirect(url_for('ctrl.categories'))
    
    # Render list of categories with pagination
    page = request.args.get('page', 1, type=int)
    pagination = Category.query.order_by(Category.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_POSTS_PER_PAGE'],
        error_out=False)
    categories = pagination.items
    return render_template('ctrl/categories.html', form=form,
                           remove_form=remove_form,
                           categories=categories,
                           datetimepicker=datetime.utcnow(),
                           pagination=pagination)

@ctrl.route('/remove-category', methods=['POST'])
@permission_required(Permission.ADMINISTER)
def remove_category():
    try:
        id = request.json['id']
        csrf = request.json['csrf']
    except (KeyError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Function takes two parameters: '
                       'id of the entry to be removed; csrf token',
        })
        
    category = Category.query.get_or_404(id)
    if category.posts.count():
        status = 'warning'
        message = "Category '{0}' is not empty and cannot be removed".\
                  format(category.title)
    else:
        status = 'success'
        message = "Category '{0}' has been removed".\
                  format(category.title)
        db.session.delete(category)
    return jsonify({
        'status': status,
        'message': message,
    })

@ctrl.route('/structure')
def structure():
    pass

@ctrl.route('/uploads', methods=['GET', 'POST'])
@permission_required(Permission.UPLOAD)
def uploads():
    form = UploadForm()
    remove_form = RemoveEntryForm()
    if form.validate_on_submit():
        # Save file
        filename = secure_filename(form.image.data.filename)
        form.image.data.save(os.path.join(current_app.config['PILI_UPLOADS'], filename))
        # DB
        upload = Upload(filename=filename, title=form.title.data,
                      owner=current_user._get_current_object())
        db.session.add(upload)
        flash("File '{0}' has been successfully uploaded.".format(filename),
              'success')
        return redirect(url_for('.uploads'))
    # Render template with pagination
    page = request.args.get('page', 1, type=int)
    pagination = Upload.query.order_by(Upload.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_IMAGES_PER_PAGE'],
        error_out=False)
    images = pagination.items
    return render_template('ctrl/uploads.html', form=form,
                           remove_form=remove_form,
                           images=images,
                           pagination=pagination)


@ctrl.route('/remove-upload', methods=['POST'])
@permission_required(Permission.UPLOAD)
def remove_upload():
    try:
        filename = request.json['filename']
        csrf = request.json['csrf']
    except (KeyError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Function takes two parameters: '
                       'filename to be removed; csrf token',
        })
    
    upload = Upload.query.filter_by(filename=filename).first_or_404()
    # Upload exists
    if upload:
        # Do not delete if an upload is in use
        categories = ', '.join([i.title for i in upload.categories])
        posts = ', '.join([i.title for i in upload.posts])
        if len(categories + posts):
            status = "warning"
            message = "File '{0}' is in use and cannot be removed.".format(filename)
            if len(posts):
                message += " Posts that use file: {0}".format(posts)
            if len(categories):
                message += " Categories that use file: {0}".format(categories)

        else:
            # Remove item in DB
            db.session.delete(upload)
            # Remove file on disk
            os.remove(os.path.join(current_app.config['PILI_UPLOADS'], filename))
            # Remove thumbnails if any
            for thumb in os.listdir(current_app.config['MEDIA_THUMBNAIL_FOLDER']):
                if thumb.startswith(find_thumbnail(filename)):
                    os.remove(os.path.join(current_app.config['MEDIA_THUMBNAIL_FOLDER'], thumb))
            status = "success"                
            message = "File '{0}' has been removed.".format(filename)
    else:
        status = "error"        
        message = "File '{0}' not found.".format(filename)
    return jsonify({
        'status': status,
        'message': message,
    })

"""
def remove_upload1(filename):
    upload = Upload.query.filter_by(filename=filename).first_or_404()
    # Check permissions
    if not (current_user.can(Permission.ADMINISTER) or \
        current_user.id != upload.owner.id):
        flash("You have no permission to remove '{0}'.".format(filename),
              'warning')
        return redirect(url_for('ctrl.uploads'))
    # Remove item in DB
    db.session.delete(upload)
    # Remove file on disk
    os.remove(os.path.join(current_app.config['PILI_UPLOADS'], filename))
    # Remove thumbnails if any
    for thumb in os.listdir(current_app.config['MEDIA_THUMBNAIL_FOLDER']):
        if thumb.startswith(find_thumbnail(filename)):
            os.remove(os.path.join(current_app.config['MEDIA_THUMBNAIL_FOLDER'], thumb))
    # Redirect
    flash("File '{0}' has been removed.".format(filename), 'success')
    return redirect(url_for('ctrl.uploads'))
"""

@ctrl.route('/view-upload/<filename>', methods=['GET', 'POST'])
def view_upload(filename):
    return send_from_directory(current_app.config['PILI_UPLOADS'], filename)


@ctrl.route('/comments')
@login_required
@permission_required(Permission.MODERATE)
def comments():
    remove_form = RemoveEntryForm()
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['PILI_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('ctrl/comments.html', comments=comments,
                           remove_form=remove_form,
                           pagination=pagination, page=page)


@ctrl.route('/comments/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def comments_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.comments',
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))


@ctrl.route('/comments/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def comments_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.comments',
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))

@ctrl.route('/comments/unscreen/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def comments_unscreen(id):
    comment = Comment.query.get_or_404(id)
    comment.screened = False
    db.session.add(comment)
    return redirect(url_for('.comments',
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))


@ctrl.route('/comments/screen/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def comments_screen(id):
    comment = Comment.query.get_or_404(id)
    comment.screened = True
    db.session.add(comment)
    return redirect(url_for('.comments',
                            page=request.args.get('page', 1, type=int),
                            _anchor='comment{0}'.format(id)))

@ctrl.route('/remove-comment', methods=['POST'])
@login_required
@permission_required(Permission.MODERATE)
def remove_comment():
    try:
        id = request.json['id']
        csrf = request.json['csrf']
    except (KeyError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Function takes two parameters: '
                       'id of the entry to be removed; csrf token',
        })
        
    comment = Comment.query.get_or_404(id)
    # find all replies
    descendants = []
    Comment.dfs(comment, lambda x: descendants.append(x))

    # remove all replies
    comments = ''
    for c in descendants:
        comments += str(c.id) + ', '
        db.session.delete(c)

    comments = comments.rstrip(', ')
    if comments:
        message = 'Comment {0} as well as replies: #{1} have been removed.'.\
                  format(comment.id, comments)
    else:
        message = 'Comment {0} has been removed.'.format(comment.id)

    # remove comment itself
    db.session.delete(comment)
    
    status = 'success'
    return jsonify({
        'status': status,
        'message': message,
    })

@ctrl.route('/comments/bulk', methods=['POST'])
@login_required
@permission_required(Permission.MODERATE)
def comments_bulk():
    def comments_action(comments, action):
        if action == 'remove':
            return remove(comments)
        
        msg = {'enable': 'enabled',
               'disable': 'disabled',
               'screen': 'screened',
               'unscreen': 'unscreened'}
        message = ''
        count = 0
        for id in comments:
            comment = Comment.query.get_or_404(id)
            if action == 'enable':
                comment.disabled = False
            elif action == 'disable':
                comment.disabled = True
            elif action == 'screen':
                comment.screened = True
            elif action == 'unscreen':
                comment.screened = False
            db.session.add(comment)
            message += str(id) + ', '
            count += 1
            
        message = message.rstrip(', ')
        if count > 1:
            message = 'Comments {message} have been {action}.'.\
                      format(message=message, action=msg[action])
        else:
            message = 'Comment {message} has been {action}.'.\
                      format(message=message, action=msg[action])
        return message

    def remove(comments):
        message = ''
        count = 0
        all_comments = set()
        for id in comments:
            try:
                comment = Comment.query.get(id)
                # add comment itself to a set
                all_comments.add(comment)
                # add all its descendants (replies) to a set
                Comment.dfs(comment, lambda x: all_comments.add(x))
                
            except:
                continue
        # remove comments and all the replies to them
        for c in all_comments:
            message += str(c.id) + ', '
            count += 1
            db.session.delete(c)

        message = message.rstrip(', ')
        if count > 1:
            message = 'Comments {message} have been removed.'.\
                      format(message=message)
        else:
            message = 'Comment {message} has been removed.'.\
                      format(message=message)

        return message
        
    try:
        csrf = request.json['csrf']
        comments = list(map(lambda x: int(x), request.json['comments']))
        action = request.json['action']
    except (KeyError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Function takes two parameters: '
                       'list of comments to be processed; csrf token',
        })

    message = comments_action(comments, action)
    
    return jsonify({
            'status': 'success',
            'message': message
    })

@ctrl.route('/logs')
def logs():
    return render_template('ctrl/logs.html')

@ctrl.route('/test')
def test():
    return render_template('ctrl/test.html')

