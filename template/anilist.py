import aiohttp
import asyncio
from config import ANILIST_API_URL
from pyrogram import Client

async def get_poster(anime_id: int = None):
    """Fetches the poster URL for an anime based on its Anilist ID."""
    return f"https://img.anili.st/media/{anime_id}" if anime_id else "https://envs.sh/YsH.jpg"

async def get_anime_data(anime_name: str, language: str, subtitle: str, season: str, global_settings_collection):
    """Fetches anime details from Anilist API."""
    
    query = '''
    query ($id: Int, $search: String, $seasonYear: Int) {
      Media(id: $id, type: ANIME, format_not_in: [MOVIE, MUSIC, MANGA, NOVEL, ONE_SHOT], search: $search, seasonYear: $seasonYear) {
        id
        idMal
        title {
          romaji
          english
          native
        }
        type
        format
        status(version: 2)
        description(asHtml: false)
        startDate { year month day }
        endDate { year month day }
        season
        seasonYear
        episodes
        duration
        countryOfOrigin
        source
        genres
        averageScore
        meanScore
        popularity
        trending
        favourites
        studios { nodes { name siteUrl } }
        isAdult
        nextAiringEpisode { airingAt timeUntilAiring episode }
        airingSchedule { edges { node { airingAt timeUntilAiring episode } } }
        externalLinks { url site }
        siteUrl
      }
    }
    '''
    
    variables = {'search': anime_name}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ANILIST_API_URL, json={'query': query, 'variables': variables}, timeout=10) as response:
                data = await response.json()
                
                if "data" in data and "Media" in data["data"]:
                    anime = data["data"]["Media"]
                    title = anime["title"]["english"] or anime["title"]["romaji"]
                    season = anime["season"] if not season else season
                    episodes = anime["episodes"]
                    genres = ', '.join(anime["genres"])
                    average_score = anime["averageScore"]
                    anime_id = anime.get("id")

                    # Fetch Main Hub from Global Config
                    main_hub = (global_settings_collection.find_one({'_id': 'config'}) or {}).get('main_hub', 'GenAnimeOfc')

                    poster_url = await get_poster(anime_id)

                    template = f"""
**{title}**
**──────────────────**
**➢ Season:** **{season}**
**➢ Episodes:** **{episodes}**
**➢ Audio:** **{language}**
**➢ Subtitle:** **{subtitle}**
**➢ Genres:** **{genres}**
**➢ Rating:** **{average_score}%**
**──────────────────**
**Main Hub:** **{main_hub}**
"""
                    return template, poster_url
                else:
                    return "Anime not found. Please check the name and try again.", "https://envs.sh/YsH.jpg"
        
        except asyncio.TimeoutError:
            return "The request timed out. Please try again later.", "https://envs.sh/YsH.jpg"
        
        except Exception as e:
            return f"An error occurred: {str(e)}", "https://envs.sh/YsH.jpg"

async def send_message_to_user(app: Client, chat_id: int, message: str, image_url: str = None):
    """Sends a message or image with caption to a Telegram user."""
    try:
        if image_url:
            await app.send_photo(chat_id, image_url, caption=message)
        else:
            await app.send_message(chat_id, message)
    except Exception as e:
        print(f"Error sending message: {e}")
