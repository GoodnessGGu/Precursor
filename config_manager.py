import json
import os

CONFIG_FILE = "bot_config.json"

DEFAULT_CONFIG = {
    "rr_ratio": 1.0,
    "lot_size": 0.01,
    "daily_loss_limit": 50.0,
    "ai_filter_enabled": False,
    "is_paused": False
}

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except:
                return DEFAULT_CONFIG
        return DEFAULT_CONFIG

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except:
            return False

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

# Single instance to be used across modules
config = ConfigManager()
