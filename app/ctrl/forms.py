from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, DateTimeField
from flask.ext.wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import Required, Length, Email, Regexp
from wtforms import ValidationError
from flask.ext.pagedown.fields import PageDownField
from ..models import Role, User, Post, Category
from ..filters import is_allowed_file, file_exists

class NameForm(Form):
    name = StringField('What is your name?', validators=[Required()])
    submit = SubmitField('Submit')


class EditProfileForm(Form):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        Required(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                          'Usernames must have only letters, '
                                          'numbers, dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class PostForm(Form):
    title = StringField("Title", validators=[Required(), Length(1, 128)])
    alias = StringField("URL alias", validators=[
        Required(), Length(1, 128), Regexp('^(\w|-)+$', 0,
                                           'Alias must contain only lowercase '
                                           'letters and dashes')])
    timestamp = DateTimeField("Date and time", format='%Y-%m-%d %H:%M:%S')
    body = PageDownField("Text", validators=[Required()])
    image = FileField("Image File", validators=[Regexp('^(\w|-|_|\.)+\.jpg|jpeg|png$', 0,
                                                       'Image file name must contain only '
                                                       'letters, dashes, underscores and dots')])
    tags = StringField("Tags", validators=[Length(0, 64)])
    featured = BooleanField('Featured')
    category = SelectField("Category", coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.category.choices = [(category.id, category.name)
                                for category in Category.query.order_by(Category.timestamp.desc()).all()]

    def validate_image(self, field):
        if field.data:
            raise ValidationError('Bad filename.')
            
            

class CategoryForm(Form):
    title = StringField("Title", validators=[Required(), Length(1, 128)])
    alias = StringField("URL alias", validators=[
        Required(), Length(1, 128), Regexp('^(\w|-)+$', 0,
                                           'Alias must contain only lowercase '
                                           'letters and dashes')])
    body = PageDownField("Text", validators=[Required()])
    category = SelectField("Category", coerce=int)
    featured = BooleanField('Featured')
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.category.choices = [(category.id, category.name)
                                for category in Category.query.order_by(Category.timestamp.desc()).all()]

class UploadForm(Form):
    # https://flask-wtf.readthedocs.org/en/latest/form.html#module-flask_wtf.file
    # https://stackoverflow.com/questions/21155930/flask-wtforms-filefield-not-validating
    image = FileField('Image File',
                      validators=[
                          FileRequired('File is required.'),
                          FileAllowed(['jpg', 'jpeg', 'png', 'gif'],
                                      'Only image files allowed.'), file_exists])
    submit = SubmitField('Submit')

    # https://wtforms.readthedocs.org/en/latest/validators.html#custom-validators
    
