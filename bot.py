import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import subprocess
import threading
import pymongo
import feedparser
from config import API_ID, API_HASH, BOT_TOKEN, URL_A, URL_B, START_PIC, ANILIST_API_URL, MONGO_URI

from webhook import start_webhook

from template.anilist import get_anime_data, send_message_to_user


mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["telegram_bot_db"]
user_settings_collection = db["user_settings"]
global_settings_collection = db["global_settings"]


app = Client("GenToolBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


webhook_thread = threading.Thread(target=start_webhook, daemon=True)
webhook_thread.start()


async def escape_markdown_v2(text: str) -> str:
    return text

async def send_message_to_user(chat_id: int, message: str, image_url: str = None):
    try:
        if image_url:
            await app.send_photo(
                chat_id, 
                image_url,
                caption=message,
            )
        else:
            await app.send_message(chat_id, message)
    except Exception as e:
        print(f"Error sending message: {e}")

@app.on_message(filters.command("start"))
async def start(client, message):
    chat_id = message.chat.id
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴍᴀɪɴ ʜᴜʙ", url="https://t.me/GenAnimeOfc"),
            InlineKeyboardButton("ꜱᴜᴩᴩᴏʀᴛ ᴄʜᴀɴɴᴇʟ", url="https://t.me/+z05NzRmuqjBkYTdl"),
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴩᴇʀ", url="https://t.me/darkxside78"),
        ],
    ])

    photo_url = start_pic

    await app.send_photo(
        chat_id, 
        photo_url,
        caption=(
            f"**ʙᴀᴋᴋᴀᴀᴀ {message.from_user.first_name}!!!**\n"
            f"**ɪ ᴀᴍ ᴀɴ ᴀɴɪᴍᴇ ᴜᴩʟᴏᴀᴅ ᴛᴏᴏʟ ʙᴏᴛ.**\n"
            f"**ɪ ᴡᴀs ᴄʀᴇᴀᴛᴇᴅ ᴛᴏ ᴍᴀᴋᴇ ᴀɴɪᴍᴇ ᴜᴩʟᴏᴀᴅᴇʀ's ʟɪғᴇ ᴇᴀsɪᴇʀ...**\n"
            f"**ɪ ᴀᴍ sᴛɪʟʟ ɪɴ ʙᴇᴛᴀ ᴛᴇsᴛɪɴɢ ᴠᴇʀsɪᴏɴ...**"
        ),
        reply_markup=buttons
    )

@app.on_message(filters.command("anime"))
async def anime(client, message):
    chat_id = message.chat.id
    user_setting = user_settings_collection.find_one({"chat_id": chat_id}) or {}
    language = user_setting.get('language', 'Dual')
    subtitle = user_setting.get('subtitle', 'English')
    season = user_setting.get('season', None)

    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "**Please provide an anime name.**")
        return

    anime_name = " ".join(message.text.split()[1:])
    template, cover_image = await get_anime_data(anime_name, language, subtitle, season, global_settings_collection)
    await send_message_to_user(app, chat_id, template, cover_image)

@app.on_message(filters.command("setlang"))
async def set_language(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        current = (user_settings_collection.find_one({"chat_id": chat_id}) or {}).get("language", "Dual")
        await app.send_message(chat_id, f"Current language is: {current}")
        return

    language = " ".join(message.text.split()[1:])
    user_settings_collection.update_one({"chat_id": chat_id}, {"$set": {"language": language}}, upsert=True)
    await app.send_message(chat_id, f"Language set to: {language}")

@app.on_message(filters.command("setchannel"))
async def set_main_hub(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        current = (global_settings_collection.find_one({"_id": "config"}) or {}).get("main_hub", "GenAnimeOfc")
        await app.send_message(chat_id, f"Current Main Hub is: {current}")
        return

    main_hub = " ".join(message.text.split()[1:])
    global_settings_collection.update_one({"_id": "config"}, {"$set": {"main_hub": main_hub}}, upsert=True)
    await app.send_message(chat_id, f"Main Hub set to: {main_hub}")

@app.on_message(filters.command("setsubtitle"))
async def set_subtitle(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        current = (user_settings_collection.find_one({"chat_id": chat_id}) or {}).get("subtitle", "English")
        await app.send_message(chat_id, f"Current subtitle is: {current}")
        return

    subtitle = " ".join(message.text.split()[1:])
    user_settings_collection.update_one({"chat_id": chat_id}, {"$set": {"subtitle": subtitle}}, upsert=True)
    await app.send_message(chat_id, f"Subtitle language set to: {subtitle}")

@app.on_message(filters.command("setseason"))
async def set_season(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        current = (global_settings_collection.find_one({"_id": "config"}) or {}).get("season", "Default Season")
        await app.send_message(chat_id, f"Current season is: {current}")
        return

    season = message.text.split()[1]
    if season.lower() == "{season}":
        global_settings_collection.update_one({"_id": "config"}, {"$unset": {"season": ""}}, upsert=True)
        await app.send_message(chat_id, "Season reset to fetch from Anilist.")
    else:
        global_settings_collection.update_one({"_id": "config"}, {"$set": {"season": season}}, upsert=True)
        await app.send_message(chat_id, f"Season set to: {season}")

@app.on_message(filters.command("connectnews"))
async def connect_news(client, message):
    chat_id = message.chat.id
    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "Please provide a channel id or username (without @).")
        return

    channel = " ".join(message.text.split()[1:]).strip()
    global_settings_collection.update_one({"_id": "config"}, {"$set": {"news_channel": channel}}, upsert=True)
    await app.send_message(chat_id, f"News channel set to: @{channel}")

##############################
# Background News Feed Functionality
##############################
sent_news_entries = set()  # In-memory store of sent entry IDs; consider persisting this if needed.

async def fetch_and_send_news():
    config = global_settings_collection.find_one({"_id": "config"})
    if not config or "news_channel" not in config:
        return

    news_channel = "@" + config["news_channel"]

    for url in [URL_A, URL_B]:
        feed = await asyncio.to_thread(feedparser.parse, url)

        # Reverse the feed entries to send from last to first
        entries = list(feed.entries)[::-1]

        for entry in entries:
            entry_id = entry.get('id', entry.get('link'))
            
            # Check if entry is already in MongoDB to avoid duplicates
            if not db.sent_news.find_one({"entry_id": entry_id}):
                sent_news_entries.add(entry_id)
                
                # Extract thumbnail if available
                thumbnail_url = None
                if 'media_thumbnail' in entry:
                    thumbnail_url = entry.media_thumbnail[0]['url']
                
                msg = f"<b>**{entry.title}**</b>\n"
                
                # Add summary if available
                if 'summary' in entry:
                    msg += f"\n{entry.summary}"
                
                msg += f"\n\n<a href='{entry.link}'>Read more</a>"

                try:
                    await asyncio.sleep(15)  # Adding a delay before sending
                    
                    if thumbnail_url:
                        await app.send_photo(chat_id=news_channel, photo=thumbnail_url, caption=msg)
                    else:
                        await app.send_message(chat_id=news_channel, text=msg)
                    
                    # Store sent entry in MongoDB to prevent duplication
                    db.sent_news.insert_one({"entry_id": entry_id, "title": entry.title, "link": entry.link})
                    print(f"Sent news: {entry.title}")
                except Exception as e:
                    print(f"Error sending news message: {e}")

async def news_feed_loop():
    while True:
        await fetch_and_send_news()
        await asyncio.sleep(10)

async def main():
    await app.start()
    print("Bot is running...")
    asyncio.create_task(news_feed_loop())
    await asyncio.Event().wait()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
