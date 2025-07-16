import os
from flask import Blueprint, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from flask_login import login_user
from config import ADMIN_DISCORD_IDS
from models import db, User  # Add this import


DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/login/callback")

oauth = OAuth()
discord = oauth.register(
    name="discord",
    client_id=DISCORD_CLIENT_ID,
    client_secret=DISCORD_CLIENT_SECRET,
    access_token_url="https://discord.com/api/oauth2/token",
    authorize_url="https://discord.com/api/oauth2/authorize",
    api_base_url="https://discord.com/api/",
    client_kwargs={"scope": "identify"},
)

discord_blueprint = Blueprint("discord", __name__)


@discord_blueprint.route("/")
def login():
    return discord.authorize_redirect(redirect_uri=DISCORD_REDIRECT_URI)


@discord_blueprint.route("/callback")
def callback():
    token = discord.authorize_access_token()
    user_info = discord.get("users/@me").json()

    discriminator = user_info.get("discriminator")
    if discriminator and discriminator != "0":
        username_display = f"{user_info['username']}#{discriminator}"
    else:
        username_display = user_info['username']

    # Try to find or create user
    user = User.query.filter_by(discord_id=user_info["id"]).first()
    if not user:
        user = User(
            discord_id=user_info["id"],
            discord_username=username_display,
            is_admin=user_info["id"] in ADMIN_DISCORD_IDS  # Check admin status
        )
    else:
        user.discord_username = username_display
        user.is_admin = user_info["id"] in ADMIN_DISCORD_IDS  # Update admin status

    db.session.add(user)
    db.session.commit()

    login_user(user)
    return redirect(url_for("index"))


def fetch_user_info(token):
    """Utility function if you want to fetch user data directly later."""
    return discord.get("users/@me", token=token).json()


def handle_discord_callback():
    token = oauth.discord.authorize_access_token()
    user_info = fetch_user_info(token)

    discord_id = user_info.get("id")
    discord_username = user_info.get("username")

    user = User.query.filter_by(discord_id=discord_id).first()

    if user is None:
        user = User(
            discord_id=discord_id,
            discord_username=discord_username,
            is_admin=discord_id in ADMIN_DISCORD_IDS
        )
        db.session.add(user)
    else:
        user.discord_username = discord_username  # Update username in case it changed
        user.is_admin = discord_id in ADMIN_DISCORD_IDS  # Update admin status

    db.session.commit()
    login_user(user)
    return redirect(url_for("index"))