import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
from flask import Flask

flask_app = Flask(__name__)

# Create a health check route
@flask_app.route("/health")
def health_check():
    return "OK", 200

# Run Flask app in a separate thread so it doesn't block the main bot process
import threading

def run_flask():
    flask_app.run(host='0.0.0.0', port=8000)

# Start the Flask app in a separate thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Telegram API credentials
api_id = '29478593'  # Replace with your actual API ID
api_hash = '24c3a9ded4ac74bab73cbe6dafbc8b3e'  # Replace with your actual API Hash
bot_token = '7580321526:AAGZPhU26-l-cVr7EMXO-R6GY4k6CQOH9hY'  # Replace with your bot token

# Anilist API URL
ANILIST_API_URL = 'https://graphql.anilist.co'

# This will store user settings temporarily
user_settings = {}

# Create a Pyrogram client
app = Client("bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

async def escape_markdown_v2(text: str) -> str:
    # Simply return the text as it is without escaping any characters
    return text

# Poster fetching method
async def get_poster(anime_id: int = None):
    if anime_id:
        return f"https://img.anili.st/media/{anime_id}"
    return "https://envs.sh/YsH.jpg"  # Default image if no poster found

# Fetch detailed anime data from Anilist API
async def get_anime_data(anime_name: str, language: str, subtitle: str, season: str):
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
    season
    seasonYear
    episodes
    duration
    chapters
    volumes
    countryOfOrigin
    source
    hashtag
    trailer {
      id
      site
      thumbnail
    }
    updatedAt
    coverImage {
      large
    }
    bannerImage
    genres
    synonyms
    averageScore
    meanScore
    popularity
    trending
    favourites
    studios {
      nodes {
         name
         siteUrl
      }
    }
    isAdult
    nextAiringEpisode {
      airingAt
      timeUntilAiring
      episode
    }
    airingSchedule {
      edges {
        node {
          airingAt
          timeUntilAiring
          episode
        }
      }
    }
    externalLinks {
      url
      site
    }
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
                    anime_id = anime.get("id")  # Get anime ID for poster URL
                    
                    # Get the poster URL asynchronously
                    poster_url = await get_poster(anime_id)

                    # Use user settings for language and subtitle
                    audio = language
                    subtitle = subtitle
                    
                    # Create a detailed anime template with everything in bold
                    template = f"""
**{title}**
**──────────────────**
**➢** **Season:** **{season}**
**➢** **Episodes:** **{episodes}**
**➢** **Audio:** **{audio}**
**➢** **Subtitle:** **{subtitle}**
**➢** **Genres:** **{genres}**
**➢** **Rating:** **{average_score}%**
**──────────────────**
**Main Hub:** **{user_settings.get('channel', '@GenAnimeOfc')}**
"""
                    return template, poster_url
                else:
                    return "Anime not found. Please check the name and try again.", "https://envs.sh/YsH.jpg"  # Default poster
        except asyncio.TimeoutError:
            return "The request timed out. Please try again later.", "https://envs.sh/YsH.jpg"  # Default poster
        except Exception as e:
            return f"An error occurred: {str(e)}", "https://envs.sh/YsH.jpg"  # Default poster

# Send message using Pyrogram
async def send_message_to_user(chat_id: int, message: str, image_url: str = None):
    try:
        if image_url:
            # Send the image with compression on (it will automatically apply compression)
            await app.send_photo(
                chat_id, 
                image_url,  # Image URL
                caption=message,  # Message with the template
            )
        else:
            # Just send the message without an image
            await app.send_message(chat_id, message)
    except Exception as e:
        print(f"Error sending message: {e}")

@app.on_message(filters.command("anime"))
async def anime(client, message):
    chat_id = message.chat.id

    # Get user settings (language, subtitle, and season) or use defaults
    language = user_settings.get(chat_id, {}).get('language', 'Dual')
    subtitle = user_settings.get(chat_id, {}).get('subtitle', 'English')
    season = user_settings.get(chat_id, {}).get('season', None)

    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "**Please provide an anime name.**")
        return

    anime_name = " ".join(message.text.split()[1:])
    template, cover_image = await get_anime_data(anime_name, language, subtitle, season)

    # Escape special Markdown characters for the caption
    safe_template = await escape_markdown_v2(template)

    # Send the template and poster image (with compression)
    await send_message_to_user(chat_id, safe_template, cover_image)

# Command handler for /setlang
@app.on_message(filters.command("setlang"))
async def set_language(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "Please provide a language (e.g., 'English', 'Japanese').")
        return

    language = " ".join(message.text.split()[1:])
    user_settings.setdefault(chat_id, {})['language'] = language
    await app.send_message(chat_id, f"Language set to: {language}")

# Command handler for /setsub
@app.on_message(filters.command("setsub"))
async def set_subtitle(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "Please provide a subtitle language (e.g., 'English', 'Spanish').")
        return

    subtitle = " ".join(message.text.split()[1:])
    user_settings.setdefault(chat_id, {})['subtitle'] = subtitle
    await app.send_message(chat_id, f"Subtitle language set to: {subtitle}")

# Command handler for /setseason
@app.on_message(filters.command("setseason"))
async def set_season(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "Please provide a season (e.g., 'Season 1', 'Season 2').")
        return

    season = " ".join(message.text.split()[1:])
    user_settings.setdefault(chat_id, {})['season'] = season
    await app.send_message(chat_id, f"Season set to: {season}")

# Command handler for /setchannel
@app.on_message(filters.command("setchannel"))
async def set_channel(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "Please provide a channel name (e.g., '@YourChannel').")
        return

    channel = " ".join(message.text.split()[1:])
    user_settings['channel'] = channel
    await app.send_message(chat_id, f"Channel set to: {channel}")

# Run the Pyrogram client
async def start_bot():
    await app.start()
    print("Bot is running...")
    await app.idle()

if __name__ == '__main__':
    app.run()
