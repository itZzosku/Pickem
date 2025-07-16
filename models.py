from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import PickleType
from datetime import datetime


db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(50), unique=True, nullable=False)
    discord_username = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User {self.discord_username}>"


class Pick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("pick", uselist=False))

    # Store list of 10 guild names
    picks = db.Column(MutableList.as_mutable(PickleType), nullable=False)

    def __repr__(self):
        return f"<Pick {self.user.discord_username}>"


class ActualResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    picks = db.Column(MutableList.as_mutable(PickleType), nullable=False)

    def __repr__(self):
        return "<ActualResult>"


class GuildRanking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    realm = db.Column(db.String(100), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    mythic_bosses_killed = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False)

    __table_args__ = (db.UniqueConstraint('name', 'realm', name='unique_guild'),)


class UserScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_final = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('scores', lazy=True))


class UpdateStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_update = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    next_update = db.Column(db.DateTime, nullable=False)
