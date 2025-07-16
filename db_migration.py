from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a minimal app instance for the migration
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pickem.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)


# Define the UserScore model for migration
class UserScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_final = db.Column(db.Boolean, default=False)


def migrate():
    with app.app_context():
        # Create the new table
        print("Starting migration...")
        try:
            # Create new tables
            db.create_all()
            print("Migration completed successfully!")

        except Exception as e:
            print(f"Error during migration: {str(e)}")
            return False

        return True


if __name__ == "__main__":
    # Run the migration
    success = migrate()
    if success:
        print("Database migration completed successfully!")
    else:
        print("Database migration failed!")