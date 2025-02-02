import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import subprocess
from collections import deque
from pymongo import MongoClient
from flask import Flask
from datetime import datetime

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
log_channel = '@teteetetsss'
log_img = 'https://images5.alphacoders.com/122/1223033.jpg'
client = MongoClient('mongodb+srv://nitinkumardhundhara:DARKXSIDE78@cluster0.wdive.mongodb.net/?retryWrites=true&w=majority')
db = client['AdvEncPosterTest']
users_collection = db['users']
queue_collection = db['queue']

# Anilist API URL
ANILIST_API_URL = 'https://graphql.anilist.co'

# This will store user settings temporarily
user_settings = {}

# Create a Pyrogram client
app = Client("bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

encoding_queue = deque()

async def process_queue():
    while encoding_queue:
        chat_id, video_file, video_type = encoding_queue.popleft()
        await encode_video_by_type(chat_id, video_file, video_type)

async def on_bot_start():
    log_message = "Bot has started successfully!"
    await log_to_channel(log_message, log_img)

def escape_markdown_v2(text: str) -> str:
    characters_to_escape = [
        r'_', r'`', r'~', r'|', r'$', r'-', 
        r'+', r'.', r'!', r'[', r']', r'=', r'\\'
    ]
    
    for char in characters_to_escape:
        # Using a raw string to handle backslashes properly
        text = text.replace(char, f'\\{char}')
    
    # We will allow the parentheses to remain unescaped
    text = text.replace(r'\(', '(').replace(r'\)', ')')
    
    return text

async def log_to_channel(log_message: str, photo_url: str = None):
    try:
        if photo_url:
            await app.send_photo(
                log_channel,  # Log channel ID or username
                photo_url=log_img,  # URL or file path of the photo
                caption=log_message  # The log message (e.g., bot startup message)
            )
        else:
            await app.send_message(log_channel, log_message)
    except Exception as e:
        print(f"Error sending log: {e}")

# Poster fetching method
async def get_poster(anime_id: int = None):
    if anime_id:
        return f"https://img.anili.st/media/{anime_id}"
    return "https://envs.sh/YsH.jpg"  # Default image if no poster found

# Fetch detailed anime data from Anilist API
async def get_anime_data(anime_name: str, language: str, subtitle: str, season: str):
    query = '''
    query ($search: String) {
        Media (search: $search, type: ANIME) {
            id
            title {
                romaji
                english
            }
            season
            episodes
            format
            genres
            averageScore
            coverImage {
                extraLarge
            }
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

# Default encoding settings if no custom settings are provided
DEFAULT_SETTINGS = {
    'preset': 'veryfast',
    'codec': 'libx264',
    'crf': '27',
    'video_bitrate': '150k',
    'audio_bitrate': '50k',
    'copyright': 'DARKXSIDE78',
    'audio': 'libopus',
    'video': 'h264',
    'subtitle': 'GenAnimeOfc',
    'title': 'GenAnimeOfc',
    'author': 'GenAnimeOfc',
    'artist': 'GenAnimeOfc'
}

@app.on_message(filters.command("encall"))
async def encode_all(client, message):
    chat_id = message.chat.id

    if message.reply_to_message:
        video_file = None

        if message.reply_to_message.video:
            video_file = await message.reply_to_message.download()
        elif message.reply_to_message.document:
            file_name = message.reply_to_message.document.file_name
            if file_name.endswith(('.mkv', '.mp4', '.avi', '.mov', '.webm')):
                video_file = await message.reply_to_message.download()

        if video_file:
            await app.send_message(chat_id, "Video File received\n\nDownloading, Encoding will start in a few moments...")
            buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴍᴀɪɴ ʜᴜʙ", url="https://t.me/Animes_Chidori"),
            InlineKeyboardButton("ꜱᴜᴩᴩᴏʀᴛ ᴄʜᴀɴɴᴇʟ", url="https://t.me/+z05NzRmuqjBkYTdl"),
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴩᴇʀ", url="https://t.me/darkxside78"),
        ],
    ])
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("HDRip", callback_data="HDRip"),
                    InlineKeyboardButton("1080p", callback_data="1080p"),
                ],
                [
                    InlineKeyboardButton("Cancel", callback_data="cancel"),
                ],
            ])

            users_collection.update_one({'chat_id': chat_id}, {'$set': {'video_file': video_file}}, upsert=True)
            await app.send_message(chat_id, "Please select the type of video resolution (HDRip or 1080p) you want to encode.", reply_markup=buttons)
        else:
            await app.send_message(chat_id, "Please reply to a video file (mkv, mp4, avi, etc.) or a document containing a video.")
    else:
        await app.send_message(chat_id, "Please reply to a video file (mkv, mp4, avi, etc.) or a document containing a video with /encall.")

@app.on_callback_query(filters.regex("HDRip|1080p|cancel"))
async def handle_video_type(client, callback_query):
    chat_id = callback_query.message.chat.id
    video_type = callback_query.data

    if video_type == "cancel":
        await app.send_message(chat_id, "Encoding canceled.")
        return

    user_data = users_collection.find_one({'chat_id': chat_id})
    if not user_data or 'video_file' not in user_data:
        await app.send_message(chat_id, "No video file found. Please reply to a video file and try again.")
        return

    video_file = user_data['video_file']
    encoding_queue.append((chat_id, video_file, video_type))
    await app.send_message(chat_id, f"Selected resolution: {video_type}. Added to queue. Encoding will begin shortly...")
    await process_queue()

async def encode_video_by_type(chat_id, video_file, video_type):
    resolution_scale = {
        '480p': '850x480',
        '720p': '1280x720',
        '1080p': '1920x1080'
    }

    settings = users_collection.find_one({'chat_id': chat_id}) or DEFAULT_SETTINGS

    if video_type == 'HDRip':
        resolutions = ['480p', '720p', '1080p']
    else:
        resolutions = ['480p', '720p']

    for resolution in resolutions:
        output_file = f"{video_file}_{resolution}.mkv"
        scale = resolution_scale.get(resolution)

        if resolution == '1080p' and video_type == '1080p':
            command = [
                "ffmpeg", "-i", video_file,
                "-c:v", settings['codec'],
                "-c:a", settings['audio'],
                "-b:v", settings['video_bitrate'],
                "-b:a", settings['audio_bitrate'],
                "-preset", settings['preset'],
                "-crf", settings['crf'],
                "-metadata", f"title={settings['title']}",
                "-metadata", f"author={settings['author']}",
                "-metadata", f"artist={settings['artist']}",
                "-metadata", f"copyright={settings['copyright']}",
                "-metadata:s:s", f"language={settings['subtitle']}",
                output_file
            ]
        else:
            command = [
                "ffmpeg", "-i", video_file,
                "-vf", f"scale={scale}",
                "-c:v", settings['codec'],
                "-preset", settings['preset'],
                "-crf", settings['crf'],
                "-b:v", settings['video_bitrate'],
                "-c:a", settings['audio'],
                "-b:a", settings['audio_bitrate'],
                output_file
            ]

        try:
            subprocess.run(command, check=True)
            await app.send_message(chat_id, f"Successfully encoded the video to {resolution}.")
        except subprocess.CalledProcessError as e:
            await app.send_message(chat_id, f"Error encoding the video to {resolution}: {e}")
        except Exception as e:
            await app.send_message(chat_id, f"An unexpected error occurred: {e}")

        try:
            await app.send_document(chat_id, output_file)
            await app.send_message(chat_id, f"Encoded video {resolution} has been sent.")
        except Exception as e:
            await app.send_message(chat_id, f"Failed to send the encoded video: {e}")

# Command handlers for all the different encoding options

@app.on_message(filters.command("enccodec"))
async def set_codec(client, message):
    chat_id = message.chat.id
    codec = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['codec'] = codec
    await app.send_message(chat_id, f"Codec set to: {codec}")

@app.on_message(filters.command("encpreset"))
async def set_preset(client, message):
    chat_id = message.chat.id
    preset = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['preset'] = preset
    await app.send_message(chat_id, f"Preset set to: {preset}")

@app.on_message(filters.command("encvideobitrate"))
async def set_video_bitrate(client, message):
    chat_id = message.chat.id
    video_bitrate = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['video_bitrate'] = video_bitrate
    await app.send_message(chat_id, f"Video bitrate set to: {video_bitrate}")

@app.on_message(filters.command("encaudiobitrate"))
async def set_audio_bitrate(client, message):
    chat_id = message.chat.id
    audio_bitrate = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['audio_bitrate'] = audio_bitrate
    await app.send_message(chat_id, f"Audio bitrate set to: {audio_bitrate}")

@app.on_message(filters.command("enccrf"))
async def set_crf(client, message):
    chat_id = message.chat.id
    crf = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['crf'] = crf
    await app.send_message(chat_id, f"CRF value set to: {crf}")

@app.on_message(filters.command("enccp"))
async def set_copyright(client, message):
    chat_id = message.chat.id
    copyright = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['copyright'] = copyright
    await app.send_message(chat_id, f"Copyright set to: {copyright}")

@app.on_message(filters.command("encaudiocodec"))
async def set_audio(client, message):
    chat_id = message.chat.id
    audio_codec = " ".join(message.text.split()[1:])
    
    # Check if a codec was provided
    if not audio_codec:
        await app.send_message(chat_id, "Please specify an audio codec (e.g., libopus, aac).")
        return
    
    # Store the audio codec setting in user settings
    user_settings.setdefault(chat_id, {})['audio'] = audio_codec
    await app.send_message(chat_id, f"Audio codec set to: {audio_codec}")

@app.on_message(filters.command("encvideocodec"))
async def set_video(client, message):
    chat_id = message.chat.id
    video_codec = " ".join(message.text.split()[1:])
    
    # Check if a codec was provided
    if not video_codec:
        await app.send_message(chat_id, "Please specify a video codec (e.g., libx264, h264).")
        return
    
    # Store the video codec setting in user settings
    user_settings.setdefault(chat_id, {})['video'] = video_codec
    await app.send_message(chat_id, f"Video codec set to: {video_codec}")

@app.on_message(filters.command("encsubtitle"))
async def set_subtitle(client, message):
    chat_id = message.chat.id
    subtitle = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['subtitle'] = subtitle
    await app.send_message(chat_id, f"Subtitle language set to: {subtitle}")

@app.on_message(filters.command("encauthor"))
async def set_author(client, message):
    chat_id = message.chat.id
    author = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['author'] = author
    await app.send_message(chat_id, f"Author set to: {author}")

@app.on_message(filters.command("encartist"))
async def set_artist(client, message):
    chat_id = message.chat.id
    artist = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['artist'] = artist
    await app.send_message(chat_id, f"Artist set to: {artist}")

@app.on_message(filters.command("enctitle"))
async def set_title(client, message):
    chat_id = message.chat.id
    title = " ".join(message.text.split()[1:])
    
    user_settings.setdefault(chat_id, {})['title'] = title
    await app.send_message(chat_id, f"Video title set to: {title}")

# Command to show all current settings
@app.on_message(filters.command("encsetting"))
async def show_settings(client, message):
    chat_id = message.chat.id
    settings = user_settings.get(chat_id, {})
    
    # Display current settings, using defaults if no settings are available
    settings_message = "\n".join([f"{key}: {value}" for key, value in {**DEFAULT_SETTINGS, **settings}.items()])
    await app.send_message(chat_id, f"Current encoding settings:\n{settings_message}")

@app.on_message(filters.command("start"))
async def start(client, message):
    chat_id = message.chat.id
    users_collection.update_one({'chat_id': chat_id}, {'$set': {'username': message.from_user.username}}, upsert=True)

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴍᴀɪɴ ʜᴜʙ", url="https://t.me/Animes_Chidori"),
            InlineKeyboardButton("ꜱᴜᴩᴩᴏʀᴛ ᴄʜᴀɴɴᴇʟ", url="https://t.me/+z05NzRmuqjBkYTdl"),
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴩᴇʀ", url="https://t.me/darkxside78"),
        ],
    ])

    # Collect user information
    user_name = message.from_user.first_name
    user_username = message.from_user.username
    user_id = message.from_user.id
    current_time = message.date.strftime("%Y-%m-%d %H:%M:%S")

    # Create log message
    log_message = f"""
User Started Bot:
**Name:** {user_name}
**Username:** @{user_username if user_username else 'N/A'}
**User ID:** {user_id}
**Time:** {current_time}
"""
    # Send log message to the logging channel
    await log_to_channel(log_message)

    photo_url = "https://images5.alphacoders.com/113/thumb-1920-1134698.jpg"
    await app.send_photo(
        chat_id, 
        photo_url,  # This can be a URL or local file path
        caption=(
            f"**ʙᴀᴋᴋᴀᴀᴀ** **{message.from_user.first_name}****!!!**\n"
            f"**ɪ ᴀɴ ᴀɴɪᴍᴇ ɪɴᴅᴇx ʙᴏᴛ ᴄʀᴇᴀᴛᴇᴅ ʙy ᴅᴀʀᴋxꜱɪᴅᴇ78 ꜰᴏʀ GᴇɴAɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ.**\n"
            f"**ɪ ᴄᴀɴ ᴩʀᴏᴠɪᴅᴇ yᴏᴜ ᴀɴy ᴀɴɪᴍᴇ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴ ᴛʜᴇ GᴇɴAɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ ɪɴ ᴏɴᴇ ᴄʟɪᴄᴋ.**\n"
            f"**ᴜsᴇ /help ᴛᴏ ɢᴇᴛ ᴀʟʟ ᴛʜᴇ ᴡᴏʀᴋ ɪɴғᴏ.**"
        ),
        reply_markup=buttons
    )   

@app.on_message(filters.command("users"))
async def show_users(client, message):
    user_count = users_collection.count_documents({})
    await app.send_message(message.chat.id, f"Total users using the bot: {user_count}")

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
    safe_template = escape_markdown_v2(template)

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
    await on_bot_start()
    print("Bot is running...")
    await process_queue()
    await app.idle()

if __name__ == '__main__':
    app.run() 
