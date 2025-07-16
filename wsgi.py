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
        logger.debug("Starting background updates initialization...")
        try:
            # Start periodic updates without waiting
            logger.debug("Starting periodic updates...")
            periodic_thread = threading.Thread(
                target=lambda: periodic_update(app, 300),
                daemon=True
            )
            periodic_thread.start()
            
            # Run initial update in another thread
            logger.debug("Running initial update in background...")
            def run_initial():
                try:
                    run_async_update(DEFAULT_RAID_SLUG)
                    from updater import update_user_scores
                    update_user_scores()
                    logger.debug("Initial update completed")
                except Exception as e:
                    logger.error(f"Error during initial update: {str(e)}")
            
            initial_thread = threading.Thread(target=run_initial, daemon=True)
            initial_thread.start()
            
        except Exception as e:
            logger.error(f"Error during updates initialization: {str(e)}")

try:
    # Test the app configuration
    logger.debug("Testing app configuration...")
    with app.app_context():
        logger.debug("Secret key present: %s", bool(app.secret_key))
        logger.debug("Database URI: %s", app.config["SQLALCHEMY_DATABASE_URI"])

    # Start the initialization in a background thread
    startup_thread = threading.Thread(target=initialize_updates, daemon=True)
    startup_thread.start()

except Exception as e:
    logger.error("Error during startup: %s", str(e))
    raise e

# This ensures our application and thread management works with gunicorn
application = app

if __name__ == "__main__":
    app.run()