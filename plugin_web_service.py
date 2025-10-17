import requests, urllib3
from plugin_base import PluginBase
import json

class WebService(PluginBase):
    def __init__(self, events, config):
        super().__init__(events, config)
        self.url = self.config.get('url', None) # Default device
        self.method = self.config.get('method', "POST") # Default baudrate
        self.headers = {'Content-type': 'application/json'}
        self.session = requests.Session()
        self.failure_count = 0
    
    async def onSecond(self, state):
        if self.url and self.failure_count < 5:
            try: 
                response = self.session.request(self.method, self.url, timeout=0.5, data=json.dumps(state.get_dict()), headers=self.headers)
            except requests.RequestException as e:
                self.logger.error(f"Error sending state to {self.url}: {e}")
                self.failure_count += 1
                return
            except urllib3.exceptions.MaxRetryError as e:
                self.logger.error(f"Max retries exceeded while sending state to {self.url}: {e}")
                self.logger.error(f"Disabling plugin to prevent further errors.")
                self.url = None
                return
            
            if response.status_code == 200:
                self.logger.debug(f"Successfully sent state to {self.url}")
            else:
                self.logger.error(f"Failed to send state to {self.url}, status code: {response.status_code}")
                self.logger.error(f"{response.headers}")
                self.logger.error(f"{response.text}")
        elif self.failure_count == 5:
                self.logger.error("Too many failures. Plugin disabled.")
                self.failure_count += 1
