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
                    
                    # Safe fetching for title, fall back to empty string if None
                    title = manga["title"]["english"] or manga["title"]["romaji"] or manga["title"]["native"] or "None"
                    
                    # Safe formatting for dates, fall back to "Unknown" if None
                    start_date = (
                        f"{manga['startDate']['year']}-{manga['startDate']['month']:02d}-{manga['startDate']['day']:02d}"
                        if manga.get("startDate") and None not in [manga['startDate'].get('year'), manga['startDate'].get('month'), manga['startDate'].get('day')]
                        else "Null"
                    )

                    end_date = (
                        f"{manga['endDate']['year']}-{manga['endDate']['month']:02d}-{manga['endDate']['day']:02d}"
                        if manga.get("endDate") and None not in [manga['endDate'].get('year'), manga['endDate'].get('month'), manga['endDate'].get('day')]
                        else "Null"
                    )

                    status = manga["status"]
                    
                    # Safe fetching for volumes and chapters, fall back to "N/A" if None
                    volumes = manga["volumes"] if manga["volumes"] else "N/A"
                    chapters = manga["chapters"] if manga["chapters"] else "N/A"
                    
                    # Safe fetching for genres, fall back to "N/A" if None
                    genres = ', '.join(manga["genres"]) if manga["genres"] else "N/A"
                    
                    manga_id = manga.get("id")

                    manga_hub = (global_settings_collection.find_one({'_id': 'config'}) or {}).get('manga_hub', '@FraxxManga')

                    cover_url = await get_manga_cover(manga_id)

                    

                    template = f"""
**{title}**
**──────────────────**
**➢ Type:** **Manga**
**➢ Status:** **{status if status else 'Unknown'}**
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
