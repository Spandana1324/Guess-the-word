from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import db, Player, GuessWord, GameSession, validate_password # Import the password validation function
import os
import random
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_strong_secret_key_for_word_guesser')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///word_guesser.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# --- Initial Setup on First Run ---
with app.app_context():
    db.create_all()
    # Add initial words if the table is empty
    if not GuessWord.query.first():
        initial_words = [
            "APPLE", "BRAIN", "CLOUD", "DREAM", "EAGLE",
            "FROST", "GRAIN", "HEART", "JUMBO", "KNIFE",
            "LEMON", "MAGIC", "OCEAN", "PLANT", "QUICK",
            "RIVER", "SNAKE", "TABLE", "UNITE", "VOWEL"
        ]
        for word in initial_words:
            db.session.add(GuessWord(word_text=word))
        db.session.commit()
    # Create a default admin user if one doesn't exist
    if not Player.query.filter_by(username='admin').first():
        admin_user = Player(username='admin', is_admin=True)
        try:
            admin_user.set_password('Admin@123')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user 'admin' created with password 'Admin@123'")
        except ValueError as e:
            print(f"Error creating admin user: {e}")

# --- User Authentication and Pages ---
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        player = Player.query.filter_by(username=username).first()
        if player and player.check_password(password):
            session['player_id'] = player.id
            session['username'] = player.username
            if player.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('play_game'))
        return render_template('auth.html', error="Invalid username or password.", is_login=True)
    return render_template('auth.html', is_login=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if username meets the criteria (at least 5 letters)
        if len(username) < 5 or not username.isalpha():
            return render_template('auth.html', error="Username must have at least 5 letters.", is_login=False)

        # Check if the user already exists
        if Player.query.filter_by(username=username).first():
            return render_template('auth.html', error="Username already exists.", is_login=False)
        
        # Validate the password using the function from database.py
        if not validate_password(password):
            return render_template('auth.html', error="Password must have at least 5 characters (alpha, numeric, and one of $, %, *, @).", is_login=False)
        
        new_player = Player(username=username)
        new_player.set_password(password)
        db.session.add(new_player)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('auth.html', is_login=False)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Game Logic ---
def get_current_player():
    if 'player_id' not in session:
        return None
    player = Player.query.get(session['player_id'])
    # Reset daily game count if it's a new day
    if player and player.last_played_date != datetime.date.today():
        player.last_played_date = datetime.date.today()
        player.games_today = 0
        db.session.commit()
    return player

@app.route('/play')
def play_game():
    player = get_current_player()
    if not player:
        return redirect(url_for('login'))

    if player.games_today >= 3:
        return render_template('home.html', daily_limit_reached=True)

    # Start a new game if one isn't active
    if 'current_word_id' not in session:
        all_words = GuessWord.query.all()
        target_word_obj = random.choice(all_words)
        session['current_word_id'] = target_word_obj.id
        session['guesses_made'] = 0
        session['guess_display'] = []

        new_session = GameSession(player_id=player.id, word_id=target_word_obj.id)
        db.session.add(new_session)
        db.session.commit()
        session['game_session_id'] = new_session.id
    
    return render_template('home.html', guess_history=session['guess_display'])

@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    player = get_current_player()
    if not player or 'current_word_id' not in session:
        return jsonify({"error": "No active game session."}), 400

    guess_text = request.json['guess'].upper()
    if len(guess_text) != 5:
        return jsonify({"error": "Guess must be a 5-letter word."}), 400

    target_word_obj = GuessWord.query.get(session['current_word_id'])
    target_word = target_word_obj.word_text
    
    # Game logic for coloring
    result = []
    temp_target = list(target_word)
    
    # First pass for green letters
    for i in range(5):
        if guess_text[i] == target_word[i]:
            result.append({'letter': guess_text[i], 'color': 'green'})
            temp_target[i] = None
        else:
            result.append({'letter': guess_text[i], 'color': 'grey'})
    
    # Second pass for orange letters
    for i in range(5):
        if result[i]['color'] == 'grey' and guess_text[i] in temp_target:
            result[i]['color'] = 'orange'
            temp_target[temp_target.index(guess_text[i])] = None

    session['guess_display'].append({'guess': guess_text, 'result': result})
    session['guesses_made'] += 1

    game_session = GameSession.query.get(session['game_session_id'])
    game_session.guesses_count = session['guesses_made']
    db.session.commit()

    response = {
        "guess_history": session['guess_display'],
        "guesses_left": 5 - session['guesses_made']
    }

    if guess_text == target_word:
        response['game_over'] = True
        response['message'] = "Congratulations, you won!"
        game_session.is_correct = True
        player.games_today += 1
        db.session.commit()
        session.pop('current_word_id', None)
    elif session['guesses_made'] >= 5:
        response['game_over'] = True
        response['message'] = f"Better luck next time! The word was {target_word}."
        player.games_today += 1
        db.session.commit()
        session.pop('current_word_id', None)
    
    return jsonify(response)

# --- Admin Reports ---
@app.route('/admin')
def admin_dashboard():
    if 'player_id' not in session or not Player.query.get(session['player_id']).is_admin:
        return "Access Denied", 403
    return render_template('admin_dashboard.html')

@app.route('/api/daily_report')
def daily_report():
    if 'player_id' not in session or not Player.query.get(session['player_id']).is_admin:
        return jsonify({"error": "Access Denied"}), 403
    
    today = datetime.date.today()
    total_players = db.session.query(GameSession.player_id).filter_by(session_date=today).distinct().count()
    correct_guesses = GameSession.query.filter_by(session_date=today, is_correct=True).count()
    
    return jsonify({
        "date": str(today),
        "total_players": total_players,
        "correct_guesses": correct_guesses
    })

@app.route('/api/user_report/<int:user_id>')
def user_report(user_id):
    if 'player_id' not in session or not Player.query.get(session['player_id']).is_admin:
        return jsonify({"error": "Access Denied"}), 403
    
    player = Player.query.get(user_id)
    if not player:
        return jsonify({"error": "Player not found."}), 404
    
    game_data = GameSession.query.filter_by(player_id=user_id).order_by(GameSession.session_date.desc()).all()
    
    report = [{
        "date": str(g.session_date),
        "words_tried": g.guesses_count,
        "correct_guess": g.is_correct
    } for g in game_data]
    
    return jsonify({"username": player.username, "report": report})

if __name__ == '__main__':
    app.run(debug=True)