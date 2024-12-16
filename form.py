from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, validators, ValidationError
from .model import User
from werkzeug.security import check_password_hash,generate_password_hash


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[validators.input_required()])
    password = PasswordField('Password', validators=[validators.input_required()])

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if not user:
            raise ValidationError('Login Fail')

    def validate_password(self, field):
        user = User.query.filter_by(email=self.email.data).first()
        if not user or not check_password_hash(user.password, field.data):
            raise ValidationError('Login Fail')


class SignupForm(FlaskForm):
    username = StringField('User Name', validators=[validators.Length(min=3, max=40), validators.input_required()])
    email = EmailField('Email', validators=[validators.input_required()])
    password1 = PasswordField('Password', validators=[validators.Length(min=8, max=20), validators.input_required()])
    password2 = PasswordField('Confirm Password', validators=[validators.Length(min=8, max=20), validators.input_required()])

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError('Email has registered.')

    def validate_password2(self, field):
        if self.password1.data != field.data:
            raise ValidationError('Password not match Confirm Password.') 
