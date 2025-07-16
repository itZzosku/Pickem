import os
from dotenv import load_dotenv

load_dotenv()  # This loads variables from .env into os.environ

ADMIN_DISCORD_IDS = os.getenv("ADMIN_DISCORD_IDS", "").split(",")