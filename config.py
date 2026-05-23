import os
import re
import logging
from typing import Dict, Any
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")

# Set up logging for configuration changes
logger = logging.getLogger("ConfigManager")

class AppConfig:
    def __init__(self):
        self.configs = {}
        self.stats = {
            "processed": 0,
            "telegram_success": 0,
            "discord_success": 0,
            "failures": 0
        }
        self.load()

    def load(self):
        """Loads or reloads configuration variables from the .env file."""
        load_dotenv(dotenv_path=env_path, override=True)
        self.configs = {
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            "TELEGRAM_SOURCE_CHANNEL": os.getenv("TELEGRAM_SOURCE_CHANNEL", "").strip(),
            "TELEGRAM_DEST_CHANNEL": os.getenv("TELEGRAM_DEST_CHANNEL", "").strip(),
            "DISCORD_MODE": os.getenv("DISCORD_MODE", "webhook").strip().lower(),
            "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
            "DISCORD_BOT_TOKEN": os.getenv("DISCORD_BOT_TOKEN", "").strip(),
            "DISCORD_CHANNEL_IDS": os.getenv("DISCORD_CHANNEL_IDS", "").strip(),
            "GPLINKS_API_TOKEN": os.getenv("GPLINKS_API_TOKEN", "a0e6a6c4443a5e524a02ea016a3dd79139a2e2a7").strip(),
            "DASHBOARD_PASSWORD": os.getenv("DASHBOARD_PASSWORD", "admin123").strip()
        }
        logger.info("Configurations loaded/reloaded from .env")

    def save(self, new_configs: Dict[str, str]):
        """Saves a fresh dictionary of configurations back to the .env file."""
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# =========================================================================\n")
                f.write("# GPLINKS AFFILIATE DEAL FORWARDER - ENVIRONMENTAL CONFIGURATION\n")
                f.write("# =========================================================================\n\n")
                
                f.write("# [TELEGRAM CONFIGURATION]\n")
                f.write(f"TELEGRAM_BOT_TOKEN={new_configs.get('TELEGRAM_BOT_TOKEN', '').strip()}\n")
                f.write(f"TELEGRAM_SOURCE_CHANNEL={new_configs.get('TELEGRAM_SOURCE_CHANNEL', '').strip()}\n")
                f.write(f"TELEGRAM_DEST_CHANNEL={new_configs.get('TELEGRAM_DEST_CHANNEL', '').strip()}\n\n")
                
                f.write("# [DISCORD INTEGRATION]\n")
                f.write(f"DISCORD_MODE={new_configs.get('DISCORD_MODE', 'webhook').strip()}\n")
                f.write(f"DISCORD_WEBHOOK_URL={new_configs.get('DISCORD_WEBHOOK_URL', '').strip()}\n")
                f.write(f"DISCORD_BOT_TOKEN={new_configs.get('DISCORD_BOT_TOKEN', '').strip()}\n")
                f.write(f"DISCORD_CHANNEL_IDS={new_configs.get('DISCORD_CHANNEL_IDS', '').strip()}\n\n")
                
                f.write("# [GPLINKS API INTEGRATION]\n")
                f.write(f"GPLINKS_API_TOKEN={new_configs.get('GPLINKS_API_TOKEN', 'a0e6a6c4443a5e524a02ea016a3dd79139a2e2a7').strip()}\n\n")
                
                f.write("# [DASHBOARD SECURITY]\n")
                f.write(f"DASHBOARD_PASSWORD={new_configs.get('DASHBOARD_PASSWORD', 'admin123').strip()}\n")
            
            # Hot reload local configuration cache
            self.load()
            logger.info("Configurations saved and hot-reloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to write configuration changes to .env: {e}")
            raise RuntimeError(f"Failed to save settings: {e}")

# Global configuration manager instance
config_manager = AppConfig()
