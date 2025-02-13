import aiohttp
import asyncio
from config import ANILIST_API_URL
from pyrogram import Client

async def get_manga_cover(manga_id: int = None):
    """Fetches the cover URL for a manga based on its Anilist ID."""
    return f"https://img.anili.st/media/{manga_id}" if manga_id else "https://envs.sh/YsH.jpg"

async def get_manga_data(manga_name: str, language: str, global_settings_collection):
    """Fetches manga details from Anilist API."""
    
    query = '''
    query ($id: Int, $search: String) {
      Media(id: $id, type: MANGA, search: $search) {
        id
        idMal
        title {
          romaji
          english
          native
        }
        type
        status(version: 2)
        startDate { year month day }
        endDate { year month day }
        volumes
        chapters
        genres
        averageScore
        meanScore
        popularity
        trending
        favourites
        externalLinks { url site }
        siteUrl
      }
    }
    '''
    
    variables = {'search': manga_name}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(ANILIST_API_URL, json={'query': query, 'variables': variables}, timeout=10) as response:
                data = await response.json()
                
                if "data" in data and "Media" in data["data"]:
                    manga = data["data"]["Media"]
                    title = manga["title"]["english"] or manga["title"]["romaji"]
                    status = manga["status"]
                    start_date = f"{manga['startDate']['year']}-{manga['startDate']['month']:02d}-{manga['startDate']['day']:02d}" if manga["startDate"] else "Unknown"
                    end_date = "Ongoing" if not manga["endDate"] else f"{manga['endDate']['year']}-{manga['endDate']['month']:02d}-{manga['endDate']['day']:02d}"
                    volumes = manga["volumes"] if manga["volumes"] else "N/A"
                    chapters = manga["chapters"] if manga["chapters"] else "N/A"
                    genres = ', '.join(manga["genres"]) if manga["genres"] else "N/A"
                    manga_id = manga.get("id")

                    # Fetch Manga Hub from Global Config
                    manga_hub = (global_settings_collection.find_one({'_id': 'config'}) or {}).get('manga_hub', 'GenMangaOfc')

                    cover_url = await get_manga_cover(manga_id)

                    template = f"""
**{title}**
**──────────────────**
**➢ Type:** **Manga**
**➢ Status:** **{status}**
**➢ Start Date:** **{start_date}**
**➢ End Date:** **{end_date}**
**➢ Volumes:** **{volumes}**
**➢ Chapters:** **{chapters}**
**➢ Genres:** **{genres}**
**──────────────────**
**Manga Hub:** **{manga_hub}**
"""
                    return template, cover_url
                else:
                    return "Manga not found. Please check the name and try again.", "https://envs.sh/YsH.jpg"
        
        except asyncio.TimeoutError:
            return "The request timed out. Please try again later.", "https://envs.sh/YsH.jpg"
        
        except Exception as e:
            return f"An error occurred: {str(e)}", "https://envs.sh/YsH.jpg"

async def send_message_to_user_manga(app: Client, chat_id: int, message: str, image_url: str = None):
    """Sends a message or image with caption to a Telegram user."""
    try:
        if image_url:
            await app.send_photo(chat_id, image_url, caption=message)
        else:
            await app.send_message(chat_id, message)
    except Exception as e:
        print(f"Error sending message: {e}")
