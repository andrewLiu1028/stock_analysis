from .database import db
from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column
from flask_login import UserMixin


class User(UserMixin,db.Model):
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(200))
    email = mapped_column(String(200), unique=True)
    password = mapped_column(String(256))
