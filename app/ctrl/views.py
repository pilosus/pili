from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response, send_from_directory
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import ctrl
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, UploadForm, \
    CategoryForm
from .. import db
from ..models import Permission, Role, User, Post, \
    Tag, Tagification, Category, Upload
from ..decorators import admin_required, permission_required
from ..filters import sanitize_alias, sanitize_tags, sanitize_upload, \
    get_added_removed, is_allowed_file, find_thumbnail
from werkzeug import secure_filename
from datetime import datetime
import os

@ctrl.route('/', methods=['GET', 'POST'])
def posts():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
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

        flash('Your post has been published.')
        return redirect(url_for('.posts'))
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('ctrl/posts.html', form=form, posts=posts,
                           datetimepicker=datetime.utcnow(),
                           pagination=pagination)

@ctrl.route('/tag/<alias>')
def tag(alias):
    tag = Tag.query.filter_by(alias=alias).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = tag.posts.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
        error_out=False)    
    posts = pagination.items
    return render_template('tag.html', tag=tag,
                           pagination=pagination, posts=posts)

@ctrl.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
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
        flash('Your profile has been updated.')
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
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@ctrl.route('/post/<int:id>-<alias>', methods=['GET'])
def post(id, alias, parent_id=None):
    post = Post.query.get_or_404(id)
    return render_template('post.html', posts=[post], pagination=pagination)

@ctrl.route('/edit/<int:id>-<alias>', methods=['GET', 'POST'])
@login_required
def edit(id, alias):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        post.title = form.title.data
        post.alias = sanitize_alias(form.alias.data)
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
        
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id, alias=post.alias))
    form.body.data = post.body
    form.title.data = post.title
    form.alias.data = post.alias
    form.tags.data =', '.join([c.title for c in post.tags.all()])
    return render_template('edit_post.html', form=form)

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
        if query.duration >= current_app.config['MMSE_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning('Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' \
                                       % (query.statement, query.parameters, query.duration,
                                          query.context))
    return response

# TODO
@ctrl.route('/category')
def category(id, alias):
    pass


# TODO
@ctrl.route('/categories', methods=['GET', 'POST'])
def categories():
    form = CategoryForm()
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
        flash("Category has been successfully created.")
        return redirect(url_for('ctrl.categories'))
    # Render template with pagination
    page = request.args.get('page', 1, type=int)
    pagination = Category.query.order_by(Category.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
        error_out=False)
    categories = pagination.items
    return render_template('ctrl/categories.html', form=form,
                           categories=categories,
                           datetimepicker=datetime.utcnow(),
                           pagination=pagination)


@ctrl.route('/structure')
def structure():
    pass

@ctrl.route('/uploads', methods=['GET', 'POST'])
@permission_required(Permission.UPLOAD_FILES)
def uploads():
    form = UploadForm()
    if form.validate_on_submit():
        # Save file
        filename = secure_filename(form.image.data.filename)
        form.image.data.save(os.path.join(current_app.config['MMSE_UPLOADS'], filename))
        # DB
        upload = Upload(filename=filename, title=form.title.data,
                      owner=current_user._get_current_object())
        db.session.add(upload)
        flash("File {0} has been successfully uploaded.".format(filename))
        return redirect(url_for('.uploads'))
    # Render template with pagination
    page = request.args.get('page', 1, type=int)
    pagination = Upload.query.order_by(Upload.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_IMAGES_PER_PAGE'],
        error_out=False)
    images = pagination.items
    return render_template('ctrl/uploads.html', form=form, images=images,
                           pagination=pagination)


@ctrl.route('/files/<action>/<filename>', methods=['GET', 'POST'])
@permission_required(Permission.UPLOAD_FILES)
def uploaded_file(action, filename):
    upload = Upload.query.filter_by(filename=filename).first_or_404()
    if action == 'view':
        return send_from_directory(current_app.config['MMSE_UPLOADS'], filename)
    elif action == 'remove':
        # Check permissions
        if not (current_user.can(Permission.ADMINISTER) or \
            current_user.id == upload.owner.id):
            flash('You have no permission to remove {0}.'.format(filename))
            return redirect(url_for('ctrl.uploads'))
        # Remove item in DB
        db.session.delete(upload)
        # Remove file on disk
        os.remove(os.path.join(current_app.config['MMSE_UPLOADS'], filename))
        # Remove thumbnails if any
        for thumb in os.listdir(current_app.config['MEDIA_THUMBNAIL_FOLDER']):
            if thumb.startswith(find_thumbnail(filename)):
                os.remove(os.path.join(current_app.config['MEDIA_THUMBNAIL_FOLDER'], thumb))
        # Redirect
        flash('{0} has been removed.'.format(filename))
        return redirect(url_for('ctrl.uploads'))
    else:
        flash('There is no such action.')
        return redirect(url_for('ctrl.uploads'))

@ctrl.route('/logs')
def logs():
    return render_template('ctrl/logs.html')

@ctrl.route('/test')
def test():
    return render_template('ctrl/test.html')

