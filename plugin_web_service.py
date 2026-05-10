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
        self._backoff = self.make_backoff(max_delay=600)

    async def send(self, path, data):
        if not self.url:
            return
        if not self._backoff.ready():
            return  # still within backoff window

        # Account for possible missing or extra slashes
        url = self.url.rstrip('/') + '/' + path.lstrip('/')
        try:
            response = self.session.request(self.method, url, timeout=0.5, data=json.dumps(data), headers=self.headers)
        except (requests.RequestException, urllib3.exceptions.MaxRetryError) as e:
            self.logger.error(f"Error sending data to {url}: {e}")
            delay = self._backoff.failure()
            self.logger.warning(f"Retrying in {delay}s")
            return

        if response.status_code == 200:
            self.logger.debug(f"Successfully sent data to {url}")
            self._backoff.success()
        else:
            self.logger.error(f"Failed to send data to {url}, status code: {response.status_code}")
            self.logger.error(f"{response.headers}")
            self.logger.error(f"{response.text}")

    async def onSecond(self, state):
        await self.send(f"/{getattr(state.player, 'event_id', 0)}/state", state.get_dict())

    #async def onDefPilot(self, pilot_id, pilot):
    #    await self.send(f"/pilot/{pilot_id}", pilot)
    
    #async def onNewRound(self, state):
    #    self.send("/round", state.round.get_dict())