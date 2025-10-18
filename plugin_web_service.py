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

    async def send(self, path, data):
        if self.url and self.failure_count < 5:
            # Account for possible missing or extra slashes
            url = self.url.rstrip('/') + '/' + path.lstrip('/')
            try: 
                response = self.session.request(self.method, url, timeout=0.5, data=json.dumps(data), headers=self.headers)
            except requests.RequestException as e:
                self.logger.error(f"Error sending data to {url}: {e}")
                self.failure_count += 1
                return
            except urllib3.exceptions.MaxRetryError as e:
                self.logger.error(f"Max retries exceeded while sending data to {url}: {e}")
                self.logger.error(f"Disabling plugin to prevent further errors.")
                self.url = None
                return
            
            if response.status_code == 200:
                self.logger.debug(f"Successfully sent data to {url}")
            else:
                self.logger.error(f"Failed to send data to {url}, status code: {response.status_code}")
                self.logger.error(f"{response.headers}")
                self.logger.error(f"{response.text}")
        elif self.failure_count == 5:
                self.logger.error("Too many failures. Plugin disabled.")
                self.failure_count += 1

    async def onSecond(self, state):
        await self.send("/state", state.get_dict())

    #async def onDefPilot(self, pilot_id, pilot):
    #    await self.send(f"/pilot/{pilot_id}", pilot)
    
    #async def onNewRound(self, state):
    #    self.send("/round", state.round.get_dict())