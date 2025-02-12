import aiohttp
import asyncio
from pyrogram import Client, filters
from config import ANILIST_API_URL

async def get_manga_data(manga_name: str, chapters: str):
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
                    main_hub = (global_settings_collection.find_one({'_id': 'config'}) or {}).get('main_hub', 'GenMangaOfc')
                    
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
**Main Hub:** **{main_hub}**"""
                    return template
                else:
                    return "Manga not found. Please check the name and try again."
        except asyncio.TimeoutError:
            return "The request timed out. Please try again later."
        except Exception as e:
            return f"An error occurred: {str(e)}"

@app.on_message(filters.command("manga"))
async def manga(client, message):
    chat_id = message.chat.id
    user_setting = user_settings_collection.find_one({"chat_id": chat_id}) or {}
    chapters = user_setting.get('chapters', None)

    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "**Please provide a manga name.**")
        return

    manga_name = " ".join(message.text.split()[1:])
    template = await get_manga_data(manga_name, chapters)
    await app.send_message(chat_id, template)

@app.on_message(filters.command("setchapters"))
async def set_chapters(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        current = (user_settings_collection.find_one({"chat_id": chat_id}) or {}).get("chapters", "Fetching from Anilist")
        await app.send_message(chat_id, f"Current chapter setting is: {current}")
        return

    chapters = message.text.split()[1]
    if chapters.lower() == "{chapters}":
        user_settings_collection.update_one({"chat_id": chat_id}, {"$unset": {"chapters": ""}}, upsert=True)
        await app.send_message(chat_id, "Chapters reset to fetch from Anilist.")
    else:
        user_settings_collection.update_one({"chat_id": chat_id}, {"$set": {"chapters": chapters}}, upsert=True)
        await app.send_message(chat_id, f"Chapters set to: {chapters}")

@app.on_message(filters.command("setmangachannel"))
async def set_manga_channel(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        current = (global_settings_collection.find_one({"_id": "config"}) or {}).get("manga_hub", "GenMangaOfc")
        await app.send_message(chat_id, f"Current Manga Hub is: {current}")
        return

    manga_hub = " ".join(message.text.split()[1:])
    global_settings_collection.update_one({"_id": "config"}, {"$set": {"manga_hub": manga_hub}}, upsert=True)
    await app.send_message(chat_id, f"Manga Hub set to: {manga_hub}")
