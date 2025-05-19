from flask import Flask, render_template, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
import os, time

app = Flask(__name__)
app.secret_key = "procrastination-rpg"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///game.db"
db = SQLAlchemy(app)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strength = db.Column(db.Integer, default=1)
    intelligence = db.Column(db.Integer, default=1)
    vitality = db.Column(db.Integer, default=1)
    charisma = db.Column(db.Integer, default=1)
    current_stat = db.Column(db.String(20), default=None)
    task_start = db.Column(db.Float, default=0.0)

@app.before_request
def load_player():
    player_id = session.get("player_id")
    player = Player.query.get(player_id) if player_id else None
    if player is None:
        player = Player()
        db.session.add(player)
        db.session.commit()
        session["player_id"] = player.id

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/state")
def state():
    player = Player.query.get(session["player_id"])
    return jsonify({
        "strength": player.strength,
        "intelligence": player.intelligence,
        "vitality": player.vitality,
        "charisma": player.charisma,
        "current_stat": player.current_stat,
        "task_start": player.task_start
    })

@app.route("/start", methods=["POST"])
def start():
    player = Player.query.get(session["player_id"])
    data = request.json
    player.current_stat = data["stat"]
    player.task_start = time.time()
    db.session.commit()
    return jsonify(success=True)

@app.route("/complete", methods=["POST"])
def complete():
    player = Player.query.get(session["player_id"])
    data = request.json
    if data["success"] and player.current_stat:
        setattr(player, player.current_stat, getattr(player, player.current_stat) + 1)
    player.current_stat = None
    player.task_start = 0
    db.session.commit()
    return jsonify(success=True)

with app.app_context():
    db.create_all()
    print("Creating tables...")

if __name__ == "__main__":
    if os.environ.get("RESET_DB") == "1":
        if os.path.exists("game.db"):
            os.remove("game.db")
        with app.app_context():
            db.create_all()
    elif not os.path.exists("game.db"):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
