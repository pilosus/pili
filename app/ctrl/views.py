from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response, send_from_directory
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import get_debug_queries
from . import ctrl
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, UploadForm
from ..models import Permission, Role, User, Post, \
    Tag, Tagification
from ..decorators import admin_required, permission_required
from ..filters import sanitize_alias, sanitize_tags, sanitize_upload, \
    get_added_removed, is_allowed_file
from werkzeug import secure_filename
import os

@ctrl.route('/', methods=['GET', 'POST'])
def posts():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        ## add post
        post = Post(body=form.body.data,
                    title=form.title.data,
                    alias=sanitize_alias(form.alias.data),
                    author=current_user._get_current_object())
        db.session.add(post)
        
        ## add tags
        tags = sanitize_tags(form.tags.data)
        if tags:
            tag_aliases = [sanitize_alias(c) for c in tags]
            for c in zip(tags, tag_aliases):
                tag_title = c[0]
                tag_alias = c[1]
                tag = Tag.query.filter(Tag.alias == \
                                                 tag_alias).first()
                ## add a single tag if it doesn't exist yet
                if not tag:
                    tag = Tag(title=tag_title, alias=tag_alias)
                    db.session.add(tag)
                
                # flush session to obtain post.id and tag.id
                db.session.flush()
                cl = Tagification(tag_id=tag.id, post_id=post.id)
                db.session.add(cl)

        flash('Your post has been published.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['MMSE_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('ctrl/posts.html', form=form, posts=posts,
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
@ctrl.route('/categories')
def categories():
    pass

@ctrl.route('/structure')
def structure():
    pass

@ctrl.route('/upload', methods=['GET', 'POST'])
@ctrl.route('/upload/<dest>', methods=['GET', 'POST'])
def uploads(dest=None):
    # https://flask-wtf.readthedocs.org/en/latest/form.html#module-flask_wtf.file
    form = UploadForm()
    if form.validate_on_submit():
        if dest:
            filename = secure_filename(dest)
        else:
            filename = secure_filename(form.image.data.filename)
        form.image.data.save(os.path.join(current_app.config['MMSE_UPLOADS'], filename))
        return redirect(url_for('.uploaded_file', filename=filename))
    else:
        filename = None
    return render_template('ctrl/uploads.html', form=form, filename=filename)

@ctrl.route('/files/<filename>')
def uploaded_file(filename):
    return send_from_directory(
        current_app.config['MMSE_UPLOADS'],
        filename)

@ctrl.route('/logs')
def logs():
    return render_template('ctrl/logs.html')

