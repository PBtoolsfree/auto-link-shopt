import os
import re
import json
import time
import logging
import asyncio
import requests
import urllib.parse
import tempfile
from typing import Dict, Any, List, Tuple
from config import config_manager

# Set up dedicated logger for the bot
log_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Console logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# File logging
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(BASE_DIR, "gplinks_bot.log")
file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
file_handler.setFormatter(log_formatter)

logger = logging.getLogger("GPLinksBot")
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.propagate = False

URL_REGEX = re.compile(
    r'https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s<>"]*?)?(?=[.,;:!?")\]]?(?:\s|$))',
    re.IGNORECASE
)

# Global variables for controlling the background task
bot_task = None
is_running = False

def is_source_or_dest_url(url: str) -> bool:
    """Ignore Telegram-specific domain links like t.me or telegram.dog to avoid shortening channel links."""
    parsed = urllib.parse.urlparse(url.lower())
    domain = parsed.netloc or parsed.path
    ignored = ["t.me", "telegram.me", "telegram.dog", "tg.me", "gplinks.co", "gplinks.com", "gplinks.in"]
    return any(ig in domain for ig in ignored)

async def shorten_with_gplinks(original_url: str) -> str:
    """Shortens a URL using the GPLinks Developers API."""
    api_token = config_manager.configs.get("GPLINKS_API_TOKEN", "").strip()
    if not api_token:
        logger.warning("GPLinks API Token is empty! Returning original URL.")
        return original_url

    try:
        encoded_url = urllib.parse.quote(original_url)
        api_url = f"https://api.gplinks.com/api?api={api_token}&url={encoded_url}"
        
        # Wrap requests.get in asyncio executor
        def _get():
            return requests.get(api_url, timeout=15)
            
        response = await asyncio.to_thread(_get)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and "shortenedUrl" in data:
                short_url = data["shortenedUrl"]
                logger.info(f"Link successfully shortened: {original_url} -> {short_url}")
                return short_url
            else:
                logger.warning(f"GPLinks API returned error/unexpected response: {data}")
        else:
            logger.error(f"GPLinks API responded with HTTP status {response.status_code}: {response.text}")
            
    except Exception as e:
        logger.error(f"Failed to shorten link via GPLinks API: {e}")
        
    return original_url

async def process_and_convert_text(text: str) -> Tuple[str, List[str]]:
    """Finds all URLs, shortens them via GPLinks API, and replaces them in the message."""
    if not text:
        return "", []
        
    found_urls = URL_REGEX.findall(text)
    urls_to_convert = [u for u in found_urls if not is_source_or_dest_url(u)]
    
    if not urls_to_convert:
        return text, []
        
    logger.info(f"Found {len(urls_to_convert)} potential URLs to convert.")
    converted_text = text
    converted_urls = []
    
    for url in urls_to_convert:
        short_url = await shorten_with_gplinks(url)
        if short_url != url:
            converted_text = converted_text.replace(url, short_url)
            converted_urls.append(short_url)
            
    return converted_text, converted_urls

async def download_telegram_file(file_id: str) -> str:
    """Downloads a photo from Telegram using getFile and returns the local path."""
    bot_token = config_manager.configs.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        return ""
        
    try:
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        
        def _get_path():
            return requests.get(get_file_url, timeout=15).json()
            
        res_data = await asyncio.to_thread(_get_path)
        
        if res_data.get("ok"):
            file_path = res_data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            
            def _download():
                return requests.get(download_url, timeout=25).content
                
            file_bytes = await asyncio.to_thread(_download)
            
            # Save to local temp file
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, f"tg_{file_id}.jpg")
            with open(local_path, "wb") as f:
                f.write(file_bytes)
                
            logger.info(f"Telegram file successfully downloaded to: {local_path}")
            return local_path
            
    except Exception as e:
        logger.error(f"Failed to download Telegram media file: {e}")
        
    return ""

async def post_to_telegram(text: str, photo_file_id: str = None) -> bool:
    """Posts the compiled deal back to the public Telegram channel."""
    bot_token = config_manager.configs.get("TELEGRAM_BOT_TOKEN", "").strip()
    dest_channel = config_manager.configs.get("TELEGRAM_DEST_CHANNEL", "").strip()
    
    if not bot_token or not dest_channel:
        logger.warning("Telegram posting skipped: Missing Bot Token or Destination Channel ID.")
        return False
        
    try:
        if photo_file_id:
            api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            payload = {
                "chat_id": dest_channel,
                "photo": photo_file_id,
                "caption": text,
                "parse_mode": "HTML"
            }
        else:
            api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": dest_channel,
                "text": text,
                "parse_mode": "HTML"
            }
            
        def _post():
            return requests.post(api_url, json=payload, timeout=20)
            
        res = await asyncio.to_thread(_post)
        res.raise_for_status()
        
        config_manager.stats["telegram_success"] += 1
        logger.info("Successfully posted deal to public Telegram channel!")
        return True
    except Exception as e:
        config_manager.stats["failures"] += 1
        logger.error(f"Failed posting to Telegram public channel: {e}")
        return False

async def post_to_discord_webhook(text: str, photo_path: str = None, short_urls: List[str] = None) -> bool:
    """Dispatches the post to Discord using webhook with embedding and buttons."""
    webhook_url = config_manager.configs.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return False
        
    # Clean HTML tags for Discord markdown
    cleaned_desc = text
    # Remove raw links from description to keep the embed clean!
    cleaned_desc = URL_REGEX.sub("", cleaned_desc).strip()
    
    cleaned_desc = cleaned_desc.replace("<b>", "**").replace("</b>", "**")
    cleaned_desc = cleaned_desc.replace("<i>", "*").replace("</i>", "*")
    cleaned_desc = re.sub(r'<a href="[^"]+">([^<]+)</a>', r'\1', cleaned_desc)
    cleaned_desc = cleaned_desc.replace("<br>", "\n").replace("<br/>", "\n")
    
    # Premium embed payload
    payload = {
        "content": "@everyone",
        "embeds": [
            {
                "title": "🎬 NEW MOVIE RELEASED! 🎬",
                "description": cleaned_desc,
                "color": 16729149,  # Premium Cinematic Crimson Red (Hex: 0xff333d)
                "footer": {
                    "text": "Automated via GPLinks Movie Forwarder"
                },
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        ]
    }
    
    # If a short link was generated, add a premium native Link Button!
    if short_urls:
        payload["components"] = [
            {
                "type": 1,  # Action Row
                "components": [
                    {
                        "type": 2,  # Button Component
                        "style": 5,  # Link Button Style
                        "label": "🍿 WATCH NOW / देखने के लिए यहाँ क्लिक करें ➔",
                        "url": short_urls[0]
                    }
                ]
            }
        ]
        
    try:
        if photo_path and os.path.exists(photo_path):
            payload["embeds"][0]["image"] = {"url": "attachment://image.jpg"}
            
            def _post_with_file():
                with open(photo_path, "rb") as f:
                    files = {
                        "file": ("image.jpg", f, "image/jpeg")
                    }
                    data = {
                        "payload_json": json.dumps(payload)
                    }
                    return requests.post(webhook_url, data=data, files=files, timeout=25)
            
            res = await asyncio.to_thread(_post_with_file)
        else:
            def _post():
                return requests.post(webhook_url, json=payload, timeout=20)
            res = await asyncio.to_thread(_post)
            
        if res.status_code in [200, 201, 204]:
            config_manager.stats["discord_success"] += 1
            logger.info("Successfully posted to Discord Webhook!")
            return True
            
        logger.error(f"Discord Webhook returned status {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Failed sending to Discord Webhook: {e}")
        
    return False

async def post_to_discord_bot(text: str, photo_path: str = None, short_urls: List[str] = None) -> bool:
    """Dispatches the post to multiple Discord channel IDs using direct Bot HTTP client APIs."""
    bot_token = config_manager.configs.get("DISCORD_BOT_TOKEN", "").strip()
    channel_ids_str = config_manager.configs.get("DISCORD_CHANNEL_IDS", "").strip()
    
    if not bot_token or not channel_ids_str:
        return False
        
    channel_ids = [c.strip() for c in channel_ids_str.split(",") if c.strip().isdigit()]
    if not channel_ids:
        return False
        
    # Clean HTML tags for Discord markdown
    cleaned_desc = text
    # Remove raw links from description to keep the embed clean!
    cleaned_desc = URL_REGEX.sub("", cleaned_desc).strip()
    
    cleaned_desc = cleaned_desc.replace("<b>", "**").replace("</b>", "**")
    cleaned_desc = cleaned_desc.replace("<i>", "*").replace("</i>", "*")
    cleaned_desc = re.sub(r'<a href="[^"]+">([^<]+)</a>', r'\1', cleaned_desc)
    
    payload = {
        "content": "@everyone",
        "embeds": [
            {
                "title": "🎬 NEW MOVIE RELEASED! 🎬",
                "description": cleaned_desc,
                "color": 16729149,  # Premium Cinematic Crimson Red (Hex: 0xff333d)
                "footer": {
                    "text": "Automated via GPLinks Movie Forwarder"
                },
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
        ]
    }
    
    if short_urls:
        payload["components"] = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "🍿 WATCH NOW / देखने के लिए यहाँ क्लिक करें ➔",
                        "url": short_urls[0]
                    }
                ]
            }
        ]
        
    headers = {
        "Authorization": f"Bot {bot_token}"
    }
    
    success_count = 0
    for cid in channel_ids:
        api_url = f"https://discord.com/api/v10/channels/{cid}/messages"
        try:
            if photo_path and os.path.exists(photo_path):
                payload["embeds"][0]["image"] = {"url": "attachment://image.jpg"}
                
                def _post_bot_file():
                    with open(photo_path, "rb") as f:
                        files = {
                            "file": ("image.jpg", f, "image/jpeg")
                        }
                        data = {
                            "payload_json": json.dumps(payload)
                        }
                        return requests.post(api_url, headers=headers, data=data, files=files, timeout=25)
                        
                res = await asyncio.to_thread(_post_bot_file)
            else:
                headers["Content-Type"] = "application/json"
                def _post_bot():
                    return requests.post(api_url, headers=headers, json=payload, timeout=20)
                res = await asyncio.to_thread(_post_bot)
                
            if res.status_code in [200, 201]:
                success_count += 1
                logger.info(f"Discord Bot successfully posted to channel {cid}")
            else:
                logger.error(f"Discord Bot API returned status {res.status_code} for channel {cid}: {res.text}")
                
        except Exception as e:
            logger.error(f"Discord Bot failed to post to channel {cid}: {e}")
            
    if success_count > 0:
        config_manager.stats["discord_success"] += success_count
        return True
    return False

async def dispatch_deal(text: str, photo_file_id: str = None, short_urls: List[str] = None):
    """Processes, shortens, and dispatches the post to both Telegram and Discord."""
    # 1. Broadcaster to public Telegram channel
    await post_to_telegram(text, photo_file_id)
    
    # 2. Broadcaster to Discord
    discord_mode = config_manager.configs.get("DISCORD_MODE", "webhook").strip().lower()
    
    # Download photo to local temp file if needed for Discord
    photo_path = None
    if photo_file_id:
        photo_path = await download_telegram_file(photo_file_id)
        
    try:
        if discord_mode == "bot":
            await post_to_discord_bot(text, photo_path, short_urls)
        else:
            await post_to_discord_webhook(text, photo_path, short_urls)
    finally:
        # Guarantee media cleanup
        if photo_path and os.path.exists(photo_path):
            try:
                os.remove(photo_path)
                logger.info(f"Deleted local temporary photo file: {photo_path}")
            except Exception as cleanup_err:
                logger.error(f"Failed deleting temporary file: {cleanup_err}")

def match_channel_id(update_chat: Dict[str, Any], target_config: str) -> bool:
    """Helper to check if a chat ID or username matches the user's config input."""
    if not update_chat or not target_config:
        return False
        
    chat_id = str(update_chat.get("id", ""))
    chat_username = str(update_chat.get("username", "")).lower().strip().lstrip("@")
    
    target_clean = str(target_config).lower().strip().lstrip("@")
    
    # Check absolute string match for ID or Username
    if chat_id == target_clean or chat_username == target_clean:
        return True
        
    return False

async def process_telegram_update(update: Dict[str, Any]):
    """Analyzes a Telegram update, extracts details if from source channel, converts links, and forwards."""
    # Handle channel_post updates
    post = update.get("channel_post") or update.get("message")
    if not post:
        return
        
    chat = post.get("chat", {})
    source_channel = config_manager.configs.get("TELEGRAM_SOURCE_CHANNEL", "").strip()
    
    # Check if the post comes from our configured source channel
    if not match_channel_id(chat, source_channel):
        return
        
    logger.info(f"Incoming post detected from Source Channel ({chat.get('title', 'Unknown')})!")
    config_manager.stats["processed"] += 1
    
    # Extract Caption (for photo/media posts) or Text (for standard text posts)
    original_text = post.get("caption") or post.get("text") or ""
    
    # Shorten extracted links
    converted_text, short_urls = await process_and_convert_text(original_text)
    
    # Check for photo media
    photo_file_id = None
    if "photo" in post and isinstance(post["photo"], list) and len(post["photo"]) > 0:
        # Telegram sends multiple sizes; the last element represents the highest resolution
        photo_file_id = post["photo"][-1]["file_id"]
        logger.info(f"Extracted media file_id: {photo_file_id}")
        
    # Dispatch shortened deal to Telegram Public and Discord
    await dispatch_deal(converted_text, photo_file_id, short_urls)

async def start_polling():
    """Starts the Telegram bot polling background task runner loop."""
    global is_running
    is_running = True
    
    bot_token = config_manager.configs.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        logger.error("Can't start polling bot: TELEGRAM_BOT_TOKEN is not configured!")
        is_running = False
        return
        
    logger.info("⚡ GPLinks Affiliate Bot Service started and polling updates...")
    
    offset = 0
    while is_running:
        try:
            api_url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=30"
            
            def _get():
                return requests.get(api_url, timeout=35)
                
            response = await asyncio.to_thread(_get)
            
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("ok"):
                    updates = res_data.get("result", [])
                    for update in updates:
                        # Process update
                        await process_telegram_update(update)
                        # Shift offset past this update ID
                        offset = update["update_id"] + 1
            elif response.status_code == 401:
                logger.error("Unauthorized: Invalid Telegram Bot Token! Poller stopped.")
                is_running = False
                break
            else:
                logger.warning(f"Telegram Bot updates polling failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error inside Bot Updates polling loop: {e}")
            
        # Mild pause to keep CPU usage low
        await asyncio.sleep(1)
        
    logger.info("Bot Polling service daemon gracefully stopped.")

async def start_bot():
    """Initializes and runs the bot daemon thread task."""
    global bot_task, is_running
    if is_running:
        logger.info("Bot poller is already running.")
        return True
        
    bot_token = config_manager.configs.get("TELEGRAM_BOT_TOKEN", "").strip()
    source_channel = config_manager.configs.get("TELEGRAM_SOURCE_CHANNEL", "").strip()
    
    if not bot_token or not source_channel:
        logger.warning("Bot launch skipped: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_SOURCE_CHANNEL configuration.")
        return False
        
    bot_task = asyncio.create_task(start_polling())
    return True

async def stop_bot():
    """Tells the bot polling loop thread to gracefully shut down."""
    global is_running, bot_task
    if not is_running:
        return
        
    logger.info("Requesting Bot service daemon shutdown...")
    is_running = False
    if bot_task:
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        bot_task = None
    logger.info("Bot successfully shut down.")
