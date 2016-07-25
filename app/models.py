from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin
from app.exceptions import ValidationError
from . import db, login_manager


class Permission:
    """Permission for App's users.

    READ: 
        - read articles

    FOLLOW:
        - follow users

    WRITE: 
        - write articles
        - edit articles written by the user

    UPLOAD: 
        - upload files
        - remove own uploaded files

    COMMENT: 
        - comment to articles
        - reply to other comment

    MODERATE: 
        - remove comment
        - block user

    STRUCTURE:
        - create categories
        - remove categories
        - edit categories

    ADMINISTER: 
        - read logs
        - change other users roles
        - confirm users registration
        - send invitations to new users

    """
    READ = 0x01
    FOLLOW = 0x02
    WRITE = 0x04
    COMMENT = 0x08
    
    UPLOAD = 0x10
    MODERATE = 0x20
    STRUCTURE = 0x40
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
            'Pariah': (Permission.READ |
                       Permission.FOLLOW, False),
            'Reader': (Permission.READ |
                       Permission.FOLLOW |
                       Permission.COMMENT, True),
            'Writer': (Permission.READ |
                       Permission.FOLLOW |
                       Permission.COMMENT |
                       Permission.WRITE, False),
            'Editor': (Permission.READ |
                       Permission.FOLLOW |
                       Permission.COMMENT |
                       Permission.WRITE |
                       Permission.STRUCTURE |
                       Permission.UPLOAD, False),
            'Moderator': (Permission.READ |
                          Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.MODERATE, False),
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

class Follow(db.Model):
    """Self-referential many-to-many relationship for User model.

    Many-to-many relationship is decomposed to two one-to-many
    relationships, as SQLAlchemy cannot use give access to the custom
    fields in association table used tranparently.
    """
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    """Comment is message under a post. 
    Comment that has a parent treated as a reply. Comment with replies
    (children) represents n-ary tree.

    """
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    screened = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    ## http://docs.sqlalchemy.org/en/latest/orm/join_conditions.html
    # there several fields in Reply class whose foreign_keys are
    # 'comment.id' that's why we need an explicit use of foreign_keys
    # dict in 'replies' field here.

    # backref adds attribute 'parent' to Reply.

    # cascade options effectively destroys links to association table
    # 'replies' if any comment referring to it is deleted, i.e. to
    # delete the entries that point to a record that was deleted
    #replies = db.relationship('Reply',
    #                          foreign_keys=[Reply.parent_id],
    #                          backref=db.backref('parent', lazy='joined'),
    #                          lazy='dynamic',
    #                          cascade='all, delete-orphan')
    replies = db.relationship('Comment',
                              backref=db.backref('parent', remote_side=[id]))

    @staticmethod
    def dfs(comment, fun):
        """Traversal of the comment n-ary tree using Depth-First Search algorithm.

        Function passed as a parameter used to process a node while
        traversing the tree: print it, remove, etc.

        >>> Comment.dfs(Comment.query.first(), print)

        >>> descendants = []
        >>> Comment.dfs(Comment.query.first(), lambda x: descendants.append(x))
        """
        # comment has no replies
        if not comment.replies:
            return
        else:
            for r in comment.replies:
                # do something with a comment here
                fun(r)
                # recurr
                Comment.dfs(r, fun)

    @staticmethod
    def bfs(comment, fun):
        """Traversal of the comment n-ary tree using Breadth-First Search.

        >>> Comment.bfs(Comment.query.first(), print)
        """
        cur_level = [comment]
        while cur_level:
            next_level = []
            for c in cur_level:
                # do not touch original comment to comply with dfs version
                if not c == comment:
                    # do something with a comment
                    fun(c)
                if c.replies:
                    next_level.extend(c.replies)
            # level change
            cur_level = next_level
                
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = current_app.config['PILI_ALLOWED_COMMENT_TAGS']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id, _external=True),
            'post': url_for('api.get_post', id=self.post_id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id,
                              _external=True),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)

    def __repr__(self):
        return '<Comment %r>' % self.id


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
    
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
    tags = db.relationship('Tag', backref='author', lazy='dynamic')  
    images = db.relationship('Upload', backref='owner', lazy='dynamic')
    # one-to-many relationship as a part of many-to-many Follows model

    # lazy parameter set to 'select' by default, which means that
    # items are loaded lazily using separate SELECT statements.
    # 'joined' means that all items are to be loaded from the
    # single db query.
    # 'dynamic' returns queries instead of items itself, so the further
    # filters could be applied.
    
    # http://docs.sqlalchemy.org/en/latest/orm/relationship_api.html\
    # ?highlight=lazy#sqlalchemy.orm.relationship.params.lazy
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment',
                               foreign_keys=[Comment.author_id],
                               backref=db.backref('author', lazy='joined'),
                               #backref='author',
                               lazy='dynamic')
    # comments recieved by a user as a reply
    replies = db.relationship('Comment',
                              foreign_keys=[Comment.recipient_id],
                              backref=db.backref('recipient', lazy='joined'),
                              #backref='recipient',
                              lazy='dynamic')
    """
    # replies by the user
    replies = db.relationship('Reply',
                              foreign_keys=[Reply.repliee_id],
                              backref=db.backref('repliee', lazy='joined'),
                              lazy='dynamic',
                              cascade='all, delete-orphan')
    # replies to the user
    messages = db.relationship('Reply',
                              foreign_keys=[Reply.replier_id],
                              backref=db.backref('replier', lazy='joined'),
                              lazy='dynamic',
                              cascade='all, delete-orphan')
    """


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

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

                
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
        self.followed.append(Follow(followed=self))

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

    def has_role(self, role_name):
        return self.role.name == role_name
    
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

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)
    
    
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

    def has_role(self, role_name):
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
        return '<Tagification: post %r contains tag %r>' %\
            (self.post_id, self.tag_id)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(128))
    alias = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    image_id = db.Column(db.Integer, db.ForeignKey('uploads.id'))
    featured = db.Column(db.Boolean, default=False, index=True)
    commenting = db.Column(db.Boolean, index=True)
    
    # 1-to-many Post/Comment
    # https://stackoverflow.com/questions/18677309/flask-sqlalchemy-relationship-error
    comments = db.relationship('Comment', backref='post', lazy='dynamic',
                               foreign_keys=[Comment.post_id])
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
            'comments': url_for('api.get_post_comments', id=self.id,
                                _external=True),
            'comment_count': self.comments.count()
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
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

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
    image_id = db.Column(db.Integer, db.ForeignKey('uploads.id'))
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
    
