from flask import Flask, redirect, url_for, session, render_template, abort
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps

from models import db, User, Pick, GuildRanking, ActualResult, UpdateStatus  # Add UpdateStatus here
from datetime import datetime, timedelta, timezone
from auth import discord_blueprint, oauth, fetch_user_info
from scoring import calculate_score
from config import ADMIN_DISCORD_IDS
import json
import asyncio
from update_top10_guilds import update_rankings, AVAILABLE_RAIDS, DEFAULT_RAID_SLUG
import threading
import time
import os
from dotenv import load_dotenv
from updater import periodic_update


load_dotenv()


def run_async_update(raid_slug=None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(update_rankings(raid_slug))
    loop.close()


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pickem.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Init plugins
db.init_app(app)
oauth.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "discord.login"

# Register Discord OAuth blueprint
app.register_blueprint(discord_blueprint, url_prefix="/login")


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def delayed_initial_update():
    time.sleep(5)  # Wait 5 seconds for everything to initialize
    with app.app_context():
        run_async_update(DEFAULT_RAID_SLUG)


# Initialize everything within the app context
with app.app_context():
    db.create_all()
    
    # Create initial update status if it doesn't exist
    update_status = UpdateStatus.query.first()
    if update_status is None:
        now = datetime.now(timezone.utc)
        initial_status = UpdateStatus(
            last_update=now,
            next_update=now + timedelta(seconds=300)  # 5 minutes
        )
        db.session.add(initial_status)
        try:
            db.session.commit()
            print("Created initial update status")
        except Exception as e:
            print(f"Error creating initial update status: {e}")
            db.session.rollback()
    
    # Only run the initial update if this is the main process
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        update_thread = threading.Thread(target=delayed_initial_update)
        update_thread.start()


@app.route("/")
def index():
    return render_template("index.html", user=current_user)


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    from flask import request, flash

    # Load guild list from guilds/finnish_guilds.json
    guilds_path = os.path.join("guilds", "finnish_guilds.json")
    with open(guilds_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    guild_list = [f"{g['name']} - {g['realm']}" for g in data["guilds"]]

    if request.method == "POST":
        picks = [request.form.get(f"rank{i}") for i in range(1, 11)]
        if len(set(picks)) != 10:
            flash("Each guild must be unique!")
            return redirect(url_for("submit"))

        existing = Pick.query.filter_by(user_id=current_user.id).first()
        if existing:
            existing.picks = picks
        else:
            new_pick = Pick(user_id=current_user.id, picks=picks)
            db.session.add(new_pick)
        db.session.commit()

        # # Trigger rankings update in background
        # def update_after_submit():
        #     with app.app_context():
        #         run_async_update(DEFAULT_RAID_SLUG)
        #         from updater import update_user_scores
        #         update_user_scores()  # Update scores after rankings

        # update_thread = threading.Thread(target=update_after_submit)
        # update_thread.daemon = True
        # update_thread.start()

        flash("Pick submitted! Rankings will be updated shortly.")
        return redirect(url_for("leaderboard"))

    return render_template("submit.html", guilds=guild_list, user=current_user)


@app.route("/leaderboard")
def leaderboard():
    from models import ActualResult, GuildRanking, UserScore, UpdateStatus
    actual = ActualResult.query.first()
    results = []

    if actual:
        scores = UserScore.query.filter_by(is_final=True).all()
    else:
        scores = UserScore.query.filter_by(is_final=False).all()

    for score in scores:
        pick = Pick.query.filter_by(user_id=score.user_id).first()
        if pick:
            results.append({
                "user": pick.user.discord_username,
                "score": score.score,
                "picks": pick.picks,
                "final": actual is not None
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    current_rankings = GuildRanking.query.order_by(
        GuildRanking.mythic_bosses_killed.desc(),
        GuildRanking.rank
    ).limit(10).all()
    current_top10 = [f"{g.name} - {g.realm}" for g in current_rankings]

    # Get update status with debug printing
    update_status = UpdateStatus.query.first()
    next_update = None
    last_update = None
    if update_status:
        next_update = update_status.next_update
        last_update = update_status.last_update
        print(f"Debug - Last update: {last_update}")
        print(f"Debug - Next update: {next_update}")
    else:
        print("Debug - No update status found in database")

    return render_template(
        "leaderboard.html",
        results=results,
        current_rankings=current_top10,
        is_final=actual is not None,
        has_current_rankings=bool(current_top10),
        next_update=next_update,
        last_update=last_update
    )


@app.route("/admin")
@login_required
@admin_required
def admin():
    from models import UserScore
    all_picks = Pick.query.all()
    picks_data = []

    for pick in all_picks:
        # Get the user's latest score
        user_score = UserScore.query.filter_by(user_id=pick.user_id).first()
        score_value = user_score.score if user_score else 0
        score_updated = user_score.last_updated if user_score else None
        is_final = user_score.is_final if user_score else False

        picks_data.append({
            "user": pick.user.discord_username,
            "discord_id": pick.user.discord_id,
            "picks": pick.picks,
            "score": score_value,
            "last_updated": score_updated,
            "is_final": is_final
        })

    # Sort by score (highest first)
    picks_data.sort(key=lambda x: x["score"], reverse=True)

    return render_template("admin.html", picks=picks_data)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/my-id")
@login_required
def my_id():
    return render_template("my_id.html", user=current_user)


@app.route("/rankings")
def rankings():
    guilds = GuildRanking.query.order_by(
        GuildRanking.mythic_bosses_killed.desc(),
        GuildRanking.rank
    ).limit(25).all()
    return render_template("rankings.html", guilds=guilds)


@app.route("/update-rankings", methods=['GET', 'POST'])
@login_required
@admin_required
def trigger_rankings_update():
    from flask import request
    if request.method == 'POST':
        raid_slug = AVAILABLE_RAIDS.get(request.form.get('raid_slug'))
        if raid_slug:
            update_thread = threading.Thread(target=run_async_update, args=(raid_slug,))
            update_thread.start()
            return f"Rankings update started for {raid_slug}. Please refresh the rankings page in a few moments."
    return "Invalid raid selected", 400


if __name__ == "__main__":
    def initial_update():
        with app.app_context():
            print("Running initial update...")
            run_async_update(DEFAULT_RAID_SLUG)
            from updater import update_user_scores
            update_user_scores()
            print("Initial update completed")

    def start_periodic_update():
        time.sleep(5)  # Wait for app to initialize
        with app.app_context():
            print("Starting periodic update service...")
            periodic_update(app, 300)

    # Start both initial and periodic updates
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        # Run initial update
        initial_thread = threading.Thread(
            target=initial_update,
            daemon=True
        )
        initial_thread.start()

        # Start periodic updates
        periodic_thread = threading.Thread(
            target=start_periodic_update,
            daemon=True
        )
        periodic_thread.start()

    app.run(debug=True, use_reloader=True)