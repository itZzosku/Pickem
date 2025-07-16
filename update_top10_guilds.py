import os
import asyncio
import json
import aiohttp
from datetime import datetime, timezone
from urllib.parse import quote, quote_plus
from models import db, GuildRanking
from typing import Optional

DEFAULT_RAID_SLUG = "liberation-of-undermine"
AVAILABLE_RAIDS = {
    "liberation": "liberation-of-undermine",
    "aberrus": "aberrus-the-shadowed-crucible",
    "vault": "vault-of-the-incarnates"
}


async def fetch_guild_rank(session: aiohttp.ClientSession, region: str, realm: str, name: str, raid_slug: str) -> dict:
    """
    Fetch guild ranking data from Raider.IO API
    """
    try:
        # Normalize realm by removing special characters and converting to lowercase
        realm = realm.lower().replace("'", "").replace("-", "").strip()
        name = name.strip()
        
        url = f"https://raider.io/api/v1/guilds/profile"
        params = {
            "region": region.lower(),
            "realm": realm,
            "name": name,
            "fields": "raid_rankings,raid_progression"
        }

        headers = {"Authorization": f"Bearer {os.getenv('RAIDERIO_TOKEN')}"} if os.getenv('RAIDERIO_TOKEN') else {}
        
        async with session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                print(f"Failed to fetch {name}-{realm}: HTTP {response.status}")
                print(f"URL attempted: {str(response.url)}")
                return {
                    "name": name,
                    "realm": realm,
                    "rank": 999999,
                    "mythic_bosses_killed": 0
                }

            data = await response.json()
                
            raid_prog = data.get('raid_progression', {})
            raid_rankings = data.get('raid_rankings', {})
                
            world_rank = (
                raid_rankings.get(raid_slug, {})
                .get('mythic', {})
                .get('world', 999999)
            )
                
            mythic_bosses = (
                raid_prog.get(raid_slug, {})
                .get('mythic_bosses_killed', 0)
            )

            try:
                world_rank = int(world_rank)
                mythic_bosses = int(mythic_bosses)
            except (ValueError, TypeError):
                world_rank = 999999
                mythic_bosses = 0

            result = {
                "name": name,
                "realm": realm,
                "rank": world_rank,
                "mythic_bosses_killed": mythic_bosses
            }
                
            print(f"Processed {name}: Rank {world_rank}, Bosses {mythic_bosses}")
            return result

    except Exception as e:
        print(f"Error processing {name}-{realm}: {str(e)}")
        return {
            "name": name,
            "realm": realm,
            "rank": 999999,
            "mythic_bosses_killed": 0
        }


async def update_rankings(raid_slug=None):
    if raid_slug is None:
        raid_slug = DEFAULT_RAID_SLUG

    from models import GuildRanking, db
    from datetime import datetime

    # Load guild list
    guilds_path = os.path.join("guilds", "finnish_guilds.json")
    with open(guilds_path, "r", encoding="utf-8") as f:
        guild_data = json.load(f)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for guild in guild_data["guilds"]:
            task = fetch_guild_rank(
                session, guild["region"], guild["realm"], guild["name"], raid_slug
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        
        # Update database
        
        for result in results:
            # Normalize guild name format
            normalized_name = f"{result['name']} - {result['realm'].lower()}"
            
            existing = GuildRanking.query.filter_by(
                name=result['name'],
                realm=result['realm']
            ).first()
            
            if existing:
                existing.rank = result['rank']
                existing.mythic_bosses_killed = result['mythic_bosses_killed']
                existing.last_updated = datetime.utcnow()
            else:
                new_guild = GuildRanking(
                    name=result['name'],
                    realm=result['realm'],
                    rank=result['rank'],
                    mythic_bosses_killed=result['mythic_bosses_killed'],
                    last_updated=datetime.utcnow()
                )
                db.session.add(new_guild)
        
        try:
            db.session.commit()
        except Exception as e:
            print(f"Error committing to database: {str(e)}")
            db.session.rollback()