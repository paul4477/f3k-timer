import asyncio
import json
import time
import logging
import os
from aiohttp import web


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*"
}
 
class WebFrontend:
    def __init__(self, events, port=8080):
        self.port = port
        self.runner = None
        self.app = web.Application()
        self.ticks = 0
        self.clients = set()
        self.events = events
        self.logger = logging.getLogger(self.__class__.__name__)
        # set html/event_selector.html as the default route

        # Add route for default page
        self.app.add_routes(
            [
                web.get("/", self.handle_default_page),
                web.post("/timesync/", self.handle_timesync),
                web.get("/ws/", self.ws_handler),
            ]
        )

    async def handle_default_page(self, request):
        # Serve the static HTML file
        file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_selector.html")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return web.Response(text=content, content_type="text/html")
        except FileNotFoundError:
            return web.Response(status=404, text="Default page not found")

    # json reponse for time sync requests from web clients
    async def handle_timesync(self, request):
        data = await request.json()
        try: id = data['id']
        except: id = "null"
        body=json.dumps({"jsonrpc": "2.0", "result": time.time()*1000, "id": f"{id}" })
        return web.Response(
            content_type="application/json", body=body,
        )
            
    ## Handle control commands from web client(s) - pause, skip, reset etc
    async def ws_handler(self, request):
        self.logger.debug("in ws_handler")
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws) # Add client to list of connected clients
        self.logger.info (f"Client connected: {request.remote} Total: {len(self.clients)}")
        try:
          async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                if msg.data == 'close':
                  await ws.close()
                else:
                  self.logger.debug(f"Message from client: {msg.data}")
                  # Handle control commands from web client(s) - pause, skip, reset etc

                  try:
                      data = json.loads(msg.data)
                      command = data.get("command")
                  except Exception as e:
                      self.logger.error(f"Failed to parse message: {msg.data} ({e})")
                      continue

                  match command:
                      case "start":
                          self.logger.info("Received start command")
                          self.events.trigger(f"player.start")
                      case "pause":
                          self.logger.info("Received pause command")
                          self.events.trigger(f"player.pause")
                      case "skip_fwd":
                          self.logger.info("Received skip_fwd command")
                          self.events.trigger(f"player.skip_fwd", 15)  # skip forward 15 seconds
                      case "skip_back":
                          self.logger.info("Received skip_back command")
                          self.events.trigger(f"player.skip_back", 15)  # skip back 15 seconds
                      case "skip_previous":
                          self.logger.info("Received skip_previous command")
                          self.events.trigger(f"player.skip_previous")
                      case "skip_next":
                          self.logger.info("Received skip_next command")
                          self.events.trigger(f"player.skip_next")
                      case "goto":
                          self.logger.info("Received goto command")
                          self.events.trigger(f"player.goto", data.get("round", 0), data.get("group", 0))
                      case "quit":
                          self.logger.info("Received quit command")
                          self.events.trigger(f"player.quit")

                      case _:
                          self.logger.warning(f"Unknown command: {command}")

            elif msg.type == web.WSMsgType.ERROR:
                self.logger.debug(f"WebSocket connection closed with exception {ws.exception()}")
        finally:
          self.clients.remove(ws)
          self.logger.debug(f"Client disconnected. Total: {len(self.clients)}")
        return ws
    

    
    async def startup(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", 8080)
        await site.start()
 
    async def shutdown(self):
        if self.runner:
            await self.runner.cleanup()

    async def update(self, state):
        # Send the bits of state needed to the web clients
        msg = json.dumps({"type": "time", "T": state.slot_time, "E": state.end_time, "R": state.round.number, "G": state.round.group_number, "N": state.is_no_fly()})
        for ws in list(self.clients):
            await ws.send_str(msg)
