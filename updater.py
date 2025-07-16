import threading
import time
import os
import asyncio
from datetime import datetime, timedelta, timezone
from models import db, Pick, GuildRanking, UserScore, UpdateStatus
from scoring import calculate_score
from update_top10_guilds import update_rankings, DEFAULT_RAID_SLUG


def update_user_scores():
    """Update scores for all users based on current rankings"""
    print("Starting score update process...")
    
    current_rankings = GuildRanking.query.order_by(
        GuildRanking.mythic_bosses_killed.desc(),
        GuildRanking.rank
    ).limit(10).all()

    if not current_rankings:
        print("No rankings found in database")
        return

    current_top10 = [f"{g.name} - {g.realm}" for g in current_rankings]
    print(f"Current top 10: {current_top10}")

    # Get all picks
    all_picks = Pick.query.all()
    print(f"Processing {len(all_picks)} picks")

    for pick in all_picks:
        # Convert picks to same format as rankings
        normalized_picks = [p.lower() for p in pick.picks]
        normalized_rankings = [r.lower() for r in current_top10]
        
        score = calculate_score(normalized_picks, normalized_rankings)
        print(f"Calculated score for {pick.user.discord_username}: {score}")

        # Update or create score record
        existing_score = UserScore.query.filter_by(
            user_id=pick.user_id,
            is_final=False
        ).first()

        if existing_score:
            if existing_score.score != score:  # Only update if score changed
                existing_score.score = score
                existing_score.last_updated = datetime.utcnow()
                print(f"Updated existing score for {pick.user.discord_username}")
        else:
            new_score = UserScore(
                user_id=pick.user_id,
                score=score,
                last_updated=datetime.utcnow(),
                is_final=False
            )
            db.session.add(new_score)
            print(f"Created new score for {pick.user.discord_username}")

    try:
        db.session.commit()
        print("Successfully committed score updates")
    except Exception as e:
        print(f"Error updating scores: {str(e)}")
        db.session.rollback()


def periodic_update(app, update_interval=300):
    """Run periodic updates of rankings and scores"""
    while True:
        try:
            with app.app_context():
                if not os.environ.get('WERKZEUG_RUN_MAIN'):
                    continue
                
                now = datetime.now(timezone.utc)
                next_update = now + timedelta(seconds=update_interval)
                
                # Create or update status record
                status = UpdateStatus.query.first()
                if status is None:
                    status = UpdateStatus(
                        last_update=now,
                        next_update=next_update
                    )
                    db.session.add(status)
                else:
                    status.last_update = now
                    status.next_update = next_update
                
                print(f"\nStarting periodic update at {now}")
                print(f"Next update scheduled for {next_update}")
                
                # Update rankings
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(update_rankings(DEFAULT_RAID_SLUG))
                loop.close()

                # Update scores
                update_user_scores()
                
                # Make sure to commit the status changes
                db.session.commit()

        except Exception as e:
            print(f"Error in periodic update: {str(e)}")
            db.session.rollback()
        
        time.sleep(update_interval)