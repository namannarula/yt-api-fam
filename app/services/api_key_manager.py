import time

class APIKeyManager:
    def __init__(self, api_keys, cooldown_period=6 * 60 * 60):
        self.api_keys = api_keys
        self.cooldown_period = cooldown_period
        self.disabled_keys = {}

    def get_next_key(self):
        available_keys = [key for key in self.api_keys if key not in self.disabled_keys or self.disabled_keys[key] < time.time()]
        if not available_keys:
            raise Exception("No API keys available")
        return available_keys[0]

    def disable_key(self, key):
        self.disabled_keys[key] = time.time() + self.cooldown_period