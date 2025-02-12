import aiohttp
import asyncio
from config import ANILIST_API_URL

async def get_manga_data(manga_name: str, chapters: str, manga_hub: str):
    query = '''
    query ($search: String) {
      Media(type: MANGA, search: $search) {
        id
        title {
          romaji
          english
          native
        }
        status
        startDate {
          year
          month
          day
        }
        endDate {
          year
          month
          day
        }
        volumes
        chapters
        genres
        coverImage {
          large
        }
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
                    status = manga["status"].replace("FINISHED", "Completed").replace("RELEASING", "Ongoing")
                    start_date = f"{manga['startDate']['year']}-{manga['startDate']['month']}-{manga['startDate']['day']}"
                    end_date = f"{manga['endDate']['year']}-{manga['endDate']['month']}-{manga['endDate']['day']}" if manga['endDate']['year'] else "Ongoing"
                    volumes = manga["volumes"] or "N/A"
                    chapters = chapters if chapters else (manga["chapters"] or "N/A")
                    genres = ', '.join(manga["genres"])
                    cover_image = manga["coverImage"]["large"]  # ✅ Fetch cover image
                    
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
**Main Hub:** **{manga_hub}**"""
                    return template, cover_image  # ✅ Correct return statement
                else:
                    return "Manga not found. Please check the name and try again.", None
        except asyncio.TimeoutError:
            return "The request timed out. Please try again later.", None
        except Exception as e:
            return f"An error occurred: {str(e)}", None
