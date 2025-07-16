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
    
    try:
        # Update the UpdateStatus timestamps
        update_status = UpdateStatus.query.first()
        current_time = datetime.utcnow()
        
        if update_status:
            update_status.last_update = current_time
            update_status.next_update = current_time + timedelta(minutes=5)
            print(f"Updated timestamps - Last: {current_time}, Next: {update_status.next_update}")
        else:
            update_status = UpdateStatus(
                last_update=current_time,
                next_update=current_time + timedelta(minutes=5)
            )
            db.session.add(update_status)
            print("Created new UpdateStatus record")
        
        db.session.commit()
        
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
            normalized_picks = [p.lower() for p in pick.picks]
            normalized_rankings = [r.lower() for r in current_top10]
            
            score = calculate_score(normalized_picks, normalized_rankings)
            print(f"Calculated score for {pick.user.discord_username}: {score}")

            existing_score = UserScore.query.filter_by(
                user_id=pick.user_id,
                is_final=False
            ).first()

            if existing_score:
                if existing_score.score != score:
                    existing_score.score = score
                    existing_score.last_updated = current_time
                    print(f"Updated existing score for {pick.user.discord_username}")
            else:
                new_score = UserScore(
                    user_id=pick.user_id,
                    score=score,
                    last_updated=current_time,
                    is_final=False
                )
                db.session.add(new_score)
                print(f"Created new score for {pick.user.discord_username}")

        db.session.commit()
        print("Successfully committed all updates")

    except Exception as e:
        print(f"Error during update process: {str(e)}")
        db.session.rollback()


def periodic_update(app, interval=300):
    """Run periodic updates every interval seconds"""
    import logging
    logger = logging.getLogger(__name__)

    while True:
        with app.app_context():
            try:
                logger.debug("Starting periodic update cycle...")
                current_time = datetime.utcnow()

                # Update rankings
                from app import run_async_update, DEFAULT_RAID_SLUG
                run_async_update(DEFAULT_RAID_SLUG)
                logger.debug("Rankings updated")

                # Update scores and timestamps
                update_user_scores()
                logger.debug(f"Scores and timestamps updated at {current_time}")

            except Exception as e:
                logger.error(f"Error in periodic update: {str(e)}")

        time.sleep(interval)