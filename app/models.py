from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request, url_for
from flask.ext.login import UserMixin, AnonymousUserMixin
from app.exceptions import ValidationError
from . import db, login_manager


class Permission:
    """Permission for App's users.

    READ: - read articles

    READ used for downgrading users who abused default rights. They
    still can read, but cannot write, upload files or edit
    structure. In order to reclaim default rights, administrator's
    action needed.

    WRITE_ARTICLES: - write and edit articles

    WRITE_ARTICLES allows user to write articles, but assign them only
    to categories already existed and use image files already uploaded
    by other users.

    UPLOAD_FILES: - upload files
                  - remove own uploaded files

    UPLOAD_FILES used to grant permission of uploading image files for
    articles, categories, etc. Introduced as a separate permission
    since many users abuse image copyrights.

    EDIT_STRUCTURE: - create and edit site menu
                    - create and edit categories

    EDIT_STRUCTURE used to work with webstite menu.

    ADMINISTER: - read logs
                - change other users roles
                - confirm users registration
                - send invitations to new users

    """
    READ = 0x01
    WRITE_ARTICLES = 0x02
    UPLOAD_FILES = 0x04
    EDIT_STRUCTURE = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    # one-to-many relationship between Role and User models
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'Pariah': (Permission.READ, False),
            'Writer': (Permission.READ |
                       Permission.WRITE_ARTICLES, True),
            'Editor': (Permission.READ |
                       Permission.WRITE_ARTICLES |
                       Permission.UPLOAD_FILES |
                       Permission.EDIT_STRUCTURE, False),
            'Moderator': (Permission.READ |
                          Permission.WRITE_ARTICLES |
                          Permission.UPLOAD_FILES |
                          Permission.EDIT_STRUCTURE |
                          Permission.ADMINISTER, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    categories = db.relationship('Category', backref='author', lazy='dynamic')
    images = db.relationship('Upload', backref='owner', lazy='dynamic')

    @staticmethod
    def add_admin():
        """Create app's administrator.

        Roles should be inserted to the database prior to creation of
        the administrator user.
        """
        import random
        import string

        admin_role = Role.query.filter_by(permissions=0xff).first()
        admin = User.query.filter_by(email=current_app.config['PILI_ADMIN']).first()
        if not admin:
            admin_user = User(email=current_app.config['PILI_ADMIN'],
                              username=current_app.config['PILI_ADMIN_NAME'],
                              password=''.join(random.SystemRandom().\
                                               choice(string.ascii_uppercase + string.digits) for _ in range(10)),
                              role=admin_role,
                              confirmed=True)
            db.session.add(admin_user)
            db.session.commit()

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        writer_role = Role.query.filter_by(name='Writer').first()
        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     role=writer_role,
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['PILI_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)


    def to_json(self):
        json_user = {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts': url_for('api.get_user_posts', id=self.id, _external=True),
            'post_count': self.posts.count()
        }
        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def __repr__(self):
        return '<User %r>' % self.username

class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

### Association table for many-to-many relationship Tag/Post.
#classifications = db.Table('classifications',
#                           db.Column('tag_id', db.Integer, db.ForeignKey('tags.id')),
#                           db.Column('post_id', db.Integer, db.ForeignKey('posts.id')))

class Tagification(db.Model):
    """Association table for many-to-many relationship Tag/Post.
    """
    __tablename__ = 'tagifications'
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'),
                            primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'),
                        primary_key=True)
    def __repr__(self):
        return '<Tagification: tag %r contains post %r>' %\
            (self.tag_id, self.post_id)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(128))
    alias = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    image_id = db.Column(db.String(64), db.ForeignKey('uploads.id'))
    featured = db.Column(db.Boolean, default=False, index=True)
    # 1-to-many relationship Category/Post
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    # many-to-many relationship Tag/Post
    tags = db.relationship('Tag',
                           secondary='tagifications',
                           backref=db.backref('posts', lazy='dynamic'),
                           lazy='dynamic')

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        from app.filters import sanitize_alias
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            t = forgery_py.forgery.lorem_ipsum.title(randint(1, 5))
            a = sanitize_alias(t)
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                     title=t,
                     alias=a,
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = current_app.config['PILI_ALLOWED_TAGS']
        allowed_attrs = current_app.config['PILI_ALLOWED_ATTRIBUTES']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=allowed_attrs, strip=True))

    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)

    def __repr__(self):
        return '<Post %r>' % self.alias


db.event.listen(Post.body, 'set', Post.on_changed_body)

class Tag(db.Model):
    """Tag a post belongs to.
    """
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    alias = db.Column(db.String(64), unique=True)

    def to_json(self):
        json_tag = {
            'url': url_for('api.get_tag', alias=self.alias, _external=True),
            'id': self.id,
            'title': self.title,
            'alias': self.alias,
            'posts': url_for('api.get_tag_posts', alias=self.alias,
                                _external=True),
            'post_count': self.posts.count()
        }
        return json_tag

    
    def __repr__(self):
        return '<Tag %r>' % self.alias

    
class Category(db.Model):
    """Category a post belongs to.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(64))
    alias = db.Column(db.String(64), unique=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    image_id = db.Column(db.String(64), db.ForeignKey('uploads.id'))
    featured = db.Column(db.Boolean, default=False, index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    posts = db.relationship('Post', backref='category', lazy='dynamic',
                               foreign_keys=[Post.category_id])

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = current_app.config['PILI_ALLOWED_TAGS']
        allowed_attrs = current_app.config['PILI_ALLOWED_ATTRIBUTES']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, attributes=allowed_attrs, strip=True))

    def __repr__(self):
        return '<Category %r>' % self.alias

db.event.listen(Category.body, 'set', Category.on_changed_body)

class Structure(db.Model):
    """Hiearchy of menu items.
    
    Each item is represented by a category.
    """
    # https://stackoverflow.com/questions/38801/sql-how-to-store-and-navigate-hierarchies
    # https://stackoverflow.com/questions/23160160/how-do-design-multilevel-database-driven-menu
    __tablename__ = 'structures'
    id = db.Column(db.Integer, db.ForeignKey('categories.id'),
                   primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    distance = db.Column(db.Integer)
    
class Upload(db.Model):
    """Uploaded files.
    """
    __tablename__ = 'uploads'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(64), unique=True)
    title = db.Column(db.String(128)) # img alt/title
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    posts = db.relationship('Post', backref='image', lazy='dynamic')
    categories = db.relationship('Category', backref='image', lazy='dynamic')

    def to_json(self):
        json_tag = {
            'url': url_for('api.get_upload', filename=self.filename, _external=True),
            'id': self.id,
            'filename': self.filename,            
            'title': self.title,
            'owner_id': self.owner_id,
            'posts': url_for('api.get_upload_posts', filename=self.filename,
                                _external=True),
            'categories': url_for('api.get_upload_categories', filename=self.filename,
                                  _external=True)

        }
        return json_tag

    
    def __repr__(self):
        return '<Upload %r>' % self.filename
    
