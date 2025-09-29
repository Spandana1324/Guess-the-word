from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re

db = SQLAlchemy()

# Custom validation for user passwords
def validate_password(password):
    if len(password) < 5:
        return False
    if not re.search("[a-zA-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    if not re.search("[$%*@]", password):
        return False
    return True

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    games_today = db.Column(db.Integer, default=0)
    last_played_date = db.Column(db.Date, default=datetime.date.min)

    def set_password(self, password):
        if not validate_password(password):
            raise ValueError("Password does not meet complexity requirements.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class GuessWord(db.Model):
    __tablename__ = 'guess_words'
    id = db.Column(db.Integer, primary_key=True)
    word_text = db.Column(db.String(5), unique=True, nullable=False)

class GameSession(db.Model):
    __tablename__ = 'game_sessions'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('guess_words.id'), nullable=False)
    guesses_count = db.Column(db.Integer, default=0)
    is_correct = db.Column(db.Boolean, default=False)
    session_date = db.Column(db.Date, default=datetime.date.today)

    player = db.relationship('Player', backref=db.backref('game_history', lazy=True))
    word = db.relationship('GuessWord', backref=db.backref('game_history', lazy=True))