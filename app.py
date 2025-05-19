from flask import Flask, render_template, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
import os, time

app = Flask(__name__)
app.secret_key = "procrastination-rpg"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///game.db"
db = SQLAlchemy(app)

# --- Models ---
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strength = db.Column(db.Integer, default=0)
    intelligence = db.Column(db.Integer, default=0)
    vitality = db.Column(db.Integer, default=0)
    charisma = db.Column(db.Integer, default=0)
    gold = db.Column(db.Integer, default=0)
    current_stat = db.Column(db.String(20), default=None)
    task_start = db.Column(db.Float, default=0.0)
    health = db.Column(db.Integer, default=100)

class Monster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    health = db.Column(db.Integer, default=50)
    might = db.Column(db.Integer, default=1)

class ShopItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    icon = db.Column(db.String(100))  # path to icon in /static/icons/
    cost = db.Column(db.Integer)
    description = db.Column(db.String(200))
    effect = db.Column(db.String(50))  # e.g. "vitality+1" or custom

# --- Player Session Management ---
@app.before_request
def load_player():
    player_id = session.get("player_id")
    player = Player.query.get(player_id) if player_id else None
    if player is None:
        player = Player()
        db.session.add(player)
        db.session.commit()
        session["player_id"] = player.id

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/state")
def state():
    player = Player.query.get(session["player_id"])
    monster = Monster.query.first()
    if not monster:
        monster = Monster()
        db.session.add(monster)
        db.session.commit()
    return jsonify({
        "strength": player.strength,
        "intelligence": player.intelligence,
        "vitality": player.vitality,
        "charisma": player.charisma,
        "gold": player.gold,
        "health": player.health,
        "max_health": 100 + 10 * player.vitality,
        "current_stat": player.current_stat,
        "task_start": player.task_start,
        "monster_health": monster.health,
        "monster_max": 50
    })



@app.route("/shop")
def shop():
    items = ShopItem.query.all()
    return jsonify([
        {
            "id": item.id,
            "name": item.name,
            "icon": item.icon,
            "cost": item.cost,
            "description": item.description,
            "effect": item.effect
        }
        for item in items
    ])

@app.route("/buy", methods=["POST"])
def buy():
    player = Player.query.get(session["player_id"])
    item_id = request.json.get("item_id")
    item = ShopItem.query.get(item_id)

    if item and player.gold >= item.cost:
        player.gold -= item.cost
        apply_item_effect(player, item.effect)
        db.session.commit()
        return jsonify(success=True, message=f"Purchased {item.name}")
    return jsonify(success=False, message="Not enough gold or invalid item")

def apply_item_effect(player, effect):
    if effect and "+" in effect:
        attr, val = effect.split("+")
        val = int(val)
        if hasattr(player, attr):
            setattr(player, attr, getattr(player, attr) + val)

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

@app.route("/battle", methods=["POST"])
def battle():
    player = Player.query.get(session["player_id"])
    monster = Monster.query.first()

    # Calculate player might and health
    player_might = 10 + 5 * player.strength
    monster_might = monster.might
    max_health = 100 + 10 * player.vitality

    # Player attacks monster
    monster.health -= player_might

    if monster.health <= 0:
        # Monster dies
        player.gold += 5
        player.health = max_health
        db.session.delete(monster)
        db.session.commit()

        # Spawn a new monster
        new_monster = Monster()
        db.session.add(new_monster)
        db.session.commit()
    else:
        # Monster retaliates
        player.health -= monster_might
        if player.health < 0:
            player.health = 0

    db.session.commit()
    return jsonify(success=True)

# --- Ensure DB is initialized on Render too ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
