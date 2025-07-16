from app import app
import sys
import logging
from updater import periodic_update
import threading
from app import run_async_update, DEFAULT_RAID_SLUG
from flask import Flask

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log to stderr which gunicorn captures
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

def initialize_updates():
    with app.app_context():
        logger.debug("Running initial update...")
        try:
            # Run initial update
            run_async_update(DEFAULT_RAID_SLUG)
            from updater import update_user_scores
            update_user_scores()
            logger.debug("Initial update completed")

            # Start periodic updates
            logger.debug("Starting periodic updates...")
            periodic_update(app, 300)  # Update every 5 minutes
        except Exception as e:
            logger.error(f"Error during updates initialization: {str(e)}")

try:
    # Test the app configuration
    logger.debug("Testing app configuration...")
    with app.app_context():
        logger.debug("Secret key present: %s", bool(app.secret_key))
        logger.debug("Database URI: %s", app.config["SQLALCHEMY_DATABASE_URI"])
        
    # Start updates in a background thread
    update_thread = threading.Thread(target=initialize_updates, daemon=True)
    update_thread.start()
    
except Exception as e:
    logger.error("Error during startup: %s", str(e))
    raise e

if __name__ == "__main__":
    app.run()