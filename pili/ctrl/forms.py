from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, DateTimeField, HiddenField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import DataRequired, Required, Length, Email, Regexp
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User, Post, Category, Upload
from ..filters import is_allowed_file, file_exists


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[Required()])
    submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
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


class PostForm(FlaskForm):
    title = StringField("Title", validators=[Required(), Length(1, 128)])
    alias = StringField("URL alias", validators=[
        Required(), Length(1, 128), Regexp('^(\w|-)+$', 0,
                                           'Alias must contain only lowercase '
                                           'letters and dashes')])
    description = StringField("Description", validators=[Required(), Length(1, 160)])
    timestamp = DateTimeField("Date and time", format='%Y-%m-%d %H:%M:%S')
    body = PageDownField("Text", validators=[Required()])
    image = StringField("Image", validators=[Length(0, 64)])
    tags = StringField("Tags", validators=[Length(0, 64)])
    featured = BooleanField('Featured')
    commenting = BooleanField('Commenting', default="checked")    
    category = SelectField("Category", coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.category.choices = [(category.id, category.title)
                                for category in Category.query.order_by\
                                 (Category.timestamp.desc()).all()]

            
class EditCategoryForm(FlaskForm):
    title = StringField("Title", validators=[Required(), Length(1, 128)])
    alias = StringField("URL alias", validators=[
        Required(), Length(1, 128), Regexp('^(\w|-)+$', 0,
                                           'Alias must contain only lowercase '
                                           'letters and dashes')])
    description = StringField("Description", validators=[Required(), Length(1, 160)])
    body = PageDownField("Text", validators=[Required()])
    image = StringField("Image", validators=[Length(0, 64)])
    timestamp = DateTimeField("Date and time", format='%Y-%m-%d %H:%M:%S')
    featured = BooleanField('Featured')
    submit = SubmitField('Submit')

    # TODO: fix image field in the form. Exceptions do not show up
    #def validate_image(self, field):
    #    if not field.data:
    #        raise ValidationError('Image is required.')
    #    if not Upload.query.filter_by(filename=field.data).first():
    #        raise ValidationError('Image {filename} not found among uploads.'\
    #                              .format(filename=field.data))

    #def validate_alias(self, field):
    #    if Category.query.filter_by(alias=field.data).first():
    #        raise ValidationError('Category with such alias already exists.')


class CategoryForm(EditCategoryForm):
    def validate_alias(self, field):
        if Category.query.filter_by(alias=field.data).first():
            raise ValidationError('Category with such alias already exists.')


class UploadForm(FlaskForm):
    # https://flask-wtf.readthedocs.org/en/latest/form.html#module-flask_wtf.file
    # https://stackoverflow.com/questions/21155930/flask-wtforms-filefield-not-validating
    image = FileField('Image File',
                      validators=[
                          FileRequired('File is required.'),
                          FileAllowed(['jpg', 'jpeg', 'png', 'gif'],
                                      'Only image files allowed.'), file_exists])
    title = StringField("Title", validators=[Required(), Length(1, 128)])
    submit = SubmitField('Submit')

    # https://wtforms.readthedocs.org/en/latest/validators.html#custom-validators


class NotificationForm(FlaskForm):
    title = StringField("Title", validators=[Required(), Length(1, 128)])
    body = PageDownField("Text", validators=[Required()])
    group = SelectField('To', coerce=int, default=0)
    email = BooleanField('Send as email')
    submit = SubmitField('Submit')
    
    def __init__(self, *args, **kwargs):
        super(NotificationForm, self).__init__(*args, **kwargs)
        self.group.choices = [(group.id, "{name} group ({count})".\
                               format(name=group.name, count=User.query.\
                                      filter(User.role_id == group.id).count()))
                             for group in Role.query.order_by(Role.name).all()]
        self.group.choices.append((0, "All users ({0})".format(User.query.count())))
    

class CsrfTokenForm(FlaskForm):
    """A form used on pages with AJAX POST requests to get access to an CSRF token."""
    id = HiddenField('Entry id', validators=[Required()])
