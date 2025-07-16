from app import app
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log to stderr which gunicorn captures
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

try:
    # Test the app configuration
    logger.debug("Testing app configuration...")
    with app.app_context():
        logger.debug("Secret key present: %s", bool(app.secret_key))
        logger.debug("Database URI: %s", app.config["SQLALCHEMY_DATABASE_URI"])
except Exception as e:
    logger.error("Error during startup: %s", str(e))
    raise e

if __name__ == "__main__":
    app.run()