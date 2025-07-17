import os
from dotenv import load_dotenv

load_dotenv()  # This loads variables from .env into os.environ

# Get the IDs and ensure they are stripped of whitespace
admin_ids_raw = os.getenv("ADMIN_DISCORD_IDS", "").split(",")
ADMIN_DISCORD_IDS = [id.strip() for id in admin_ids_raw]
