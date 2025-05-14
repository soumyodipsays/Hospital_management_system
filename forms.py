from flask_wtf import FlaskForm
from wtforms import StringField,SelectField,IntegerField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional,EqualTo,NumberRange

class SignupForm(FlaskForm):
    name = StringField("Username", validators=(DataRequired(), Length(5, 25) ))
    email = StringField("Email", validators=(DataRequired(), Email()))
    gender = SelectField("Gender", validators=[Optional()], choices=[("male", "Male"), ("female", "Female"), ("others", "Others")])
    age = IntegerField("Age", validators=[Optional(),NumberRange(5,120)])
    password = PasswordField("password", validators=[DataRequired(), Length(2, 8)])
    confirm_password = PasswordField("confirm password",  validators=[DataRequired(), Length(2, 8), EqualTo("password")])
    submit = SubmitField("submit")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

