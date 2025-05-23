import time
import random
from flask import jsonify
from app import db
from models import Player, Quest

# Quest model definition
class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"))
    stat = db.Column(db.String(20))  # e.g. "strength"
    goal = db.Column(db.Integer)     # how many levels
    progress = db.Column(db.Integer, default=0)
    reward = db.Column(db.Integer)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Float)  # timestamp

# Helper function to create a new quest
def generate_quest_for_player(player):
    stat = random.choice(["strength", "intelligence", "vitality", "charisma"])
    goal = random.randint(1, 3)
    reward = goal * random.randint(1000, 1200)
    quest = Quest(
        player_id=player.id,
        stat=stat,
        goal=goal,
        progress=0,
        reward=reward,
        completed=False,
        created_at=time.time()
    )
    db.session.add(quest)
    db.session.commit()

# Call this in @before_request or /state
def check_and_refresh_quest(player):
    latest_quest = Quest.query.filter_by(player_id=player.id).order_by(Quest.created_at.desc()).first()
    now = time.time()
    if not latest_quest or (now - latest_quest.created_at > 86400):
        generate_quest_for_player(player)

# Quest progress logic (called in /complete)
def track_quest_progress(player, completed_stat):
    quest = Quest.query.filter_by(player_id=player.id, stat=completed_stat, completed=False).first()
    if quest:
        quest.progress += 1
        if quest.progress >= quest.goal:
            quest.completed = True
            player.gold += quest.reward
        db.session.commit()

# Include in /state JSON
def get_player_quest(player):
    quest = Quest.query.filter_by(player_id=player.id).order_by(Quest.created_at.desc()).first()
    if not quest:
        return None
    return {
        "stat": quest.stat,
        "goal": quest.goal,
        "progress": quest.progress,
        "reward": quest.reward,
        "completed": quest.completed,
        "created_at": quest.created_at
    }
