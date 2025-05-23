from flask import Flask, render_template, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
import os, time, random

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
    slot = db.Column(db.String(20))  # e.g., "weapon", "armor", "accessory"
    bonuses = db.Column(db.String(100))  # e.g., "strength+2;vitality+1"

class EquippedItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"))
    slot = db.Column(db.String(20))
    item_id = db.Column(db.Integer, db.ForeignKey("shop_item.id"))
    item = db.relationship("ShopItem")

class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"))
    stat = db.Column(db.String(20))  # e.g. "strength"
    goal = db.Column(db.Integer)  # how many levels
    progress = db.Column(db.Integer, default=0)
    reward = db.Column(db.Integer)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Float)  # timestamp


# --- Helpers ---
def apply_item_effect(player, effect):
    if effect and "+" in effect:
        attr, val = effect.split("+")
        val = int(val)
        if hasattr(player, attr):
            setattr(player, attr, getattr(player, attr) + val)

def apply_bonuses(player, bonuses, remove=False):
    if bonuses:
        for bonus in bonuses.split(";"):
            if "+" in bonus:
                stat, val = bonus.split("+")
                val = int(val)
                if remove:
                    val = -val
                if hasattr(player, stat):
                    setattr(player, stat, getattr(player, stat) + val)

def apply_scaled_effect(player, effect, reverse=False):
    """
    Applies effects like: scale:target=source or scale:target=source*multiplier
    Example: scale:health=vitality*5
    """
    if not effect or not effect.startswith("scale:"):
        return

    try:
        _, mapping = effect.split(":")
        target, expr = mapping.split("=")

        # Extract multiplier (default = 1)
        if "*" in expr:
            source, multiplier = expr.split("*")
            multiplier = int(multiplier)
        else:
            source = expr
            multiplier = 1

        if hasattr(player, target) and hasattr(player, source):
            value = getattr(player, source) * multiplier
            if reverse:
                value = -value
            setattr(player, target, getattr(player, target) + value)
    except Exception as e:
        print("❌ Failed to apply scaled effect:", effect, e)

def equip_item_to_player(player, item):
    if not item or not item.slot:
        return False

    existing = EquippedItem.query.filter_by(player_id=player.id, slot=item.slot).first()
    if existing:
        apply_bonuses(player, existing.item.bonuses, remove=True)
        apply_scaled_effect(player, existing.item.effect, reverse=True)
        db.session.delete(existing)

    apply_bonuses(player, item.bonuses)
    apply_scaled_effect(player, item.effect)
    equipped = EquippedItem(player_id=player.id, slot=item.slot, item_id=item.id)
    db.session.add(equipped)
    return True

def get_might(player):
    base = 1 + player.strength
    bonus = 0

    equipped_items = EquippedItem.query.filter_by(player_id=player.id).all()

    for equipped in equipped_items:
        item = equipped.item
        if item.effect and item.effect.startswith("scale:"):
            try:
                _, mapping = item.effect.split(":")
                target, expr = mapping.split("=")

                # Support multiplier: source*factor
                if "*" in expr:
                    source, factor = expr.split("*")
                    factor = int(factor)
                else:
                    source = expr
                    factor = 1

                if target in ("strength", "might") and hasattr(player, source):
                    val = getattr(player, source)
                    bonus += val * factor

            except Exception as e:
                print(f"Error parsing scaled might effect: {item.effect}", e)

    return base + bonus

def generate_quest_for_player(player):
    stat = random.choice(["strength", "intelligence", "vitality", "charisma"])
    goal = random.randint(1, 3)
    reward = goal * random.randint(1000, 1200)
    quest = Quest(
        player_id=player.id, stat=stat, goal=goal,
        reward=reward, progress=0, completed=False,
        created_at=time.time()
    )
    db.session.add(quest)
    db.session.commit()

def check_and_refresh_quest(player):
    q = Quest.query.filter_by(player_id=player.id).order_by(Quest.created_at.desc()).first()
    now = time.time()
    if not q or now - q.created_at > 86400:
        generate_quest_for_player(player)

def track_quest_progress(player, stat):
    q = Quest.query.filter_by(player_id=player.id, stat=stat, completed=False).first()
    if q:
        q.progress += 1
        if q.progress >= q.goal:
            q.completed = True
            player.gold += q.reward
        db.session.commit()

def get_player_quest(player):
    q = Quest.query.filter_by(player_id=player.id).order_by(Quest.created_at.desc()).first()
    if not q:
        return None
    return {
        "stat": q.stat,
        "goal": q.goal,
        "progress": q.progress,
        "reward": q.reward,
        "completed": q.completed,
        "created_at": q.created_at
    }

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
    check_and_refresh_quest(player)
    monster = Monster.query.first()
    if not monster:
        monster = Monster()
        db.session.add(monster)
        db.session.commit()

    equipped_items = EquippedItem.query.filter_by(player_id=player.id).all()
    equipment = {e.slot: e.item.name for e in equipped_items}
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
        "monster_max": 50,
        "equipment": equipment,
        "quest": get_player_quest(player)
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
            "effect": item.effect,
            "slot": item.slot,
            "bonuses": item.bonuses
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

        if item.effect:
            apply_item_effect(player, item.effect)

        if item.slot and item.bonuses:
            equip_item_to_player(player, item)

        db.session.commit()
        return jsonify(success=True, message=f"Purchased {item.name}")
    return jsonify(success=False, message="Not enough gold or invalid item")

@app.route("/equip", methods=["POST"])
def equip_item():
    player = Player.query.get(session["player_id"])
    item_id = request.json.get("item_id")
    item = ShopItem.query.get(item_id)

    success = equip_item_to_player(player, item)
    if success:
        db.session.commit()
        return jsonify(success=True, message=f"Equipped {item.name}")
    return jsonify(success=False, message="Invalid item or slot")

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
        track_quest_progress(player, player.current_stat)
    player.current_stat = None
    player.task_start = 0
    db.session.commit()
    return jsonify(success=True)


@app.route("/battle", methods=["POST"])
def battle():
    player = Player.query.get(session["player_id"])
    monster = Monster.query.first()

    player_might = get_might(player)
    player_damage = player_might * 10
    monster_might = monster.might
    max_health = 100 + 10 * player.vitality

    monster.health -= player_damage

    if monster.health <= 0:
        player.gold += 5
        player.health = max_health
        db.session.delete(monster)
        db.session.commit()
        new_monster = Monster()
        db.session.add(new_monster)
        db.session.commit()
    else:
        player.health -= monster_might
        if player.health < 0:
            player.health = 0

    db.session.commit()
    return jsonify(success=True)

@app.route("/add-gold", methods=["POST"])
def add_gold():
    player = Player.query.get(session["player_id"])
    player.gold += 50
    db.session.commit()
    return jsonify(success=True)


# --- Ensure DB is initialized on Render too ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
