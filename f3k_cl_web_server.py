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
        self.event_data_loaded = False
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_update = 0
        # Add route for default page
        
        self.app.add_routes(
            [
                web.static("/assets/", os.path.join(os.path.dirname(__file__), "assets")),
                web.get("/", self.handle_default_page),
                
                web.get("/run", self.handle_run_page),
                web.get("/reset", self.handle_reset),
                web.post("/timesync/", self.handle_timesync),
                web.get("/ws/", self.ws_handler),
                web.post("/load_event", self.handle_load_event),
                
            ]
        )
    async def handle_reset(self, request):
        # Serve the static HTML file
        self.logger.debug(f"Resetting event data, {self.event_data_loaded}")
        if self.event_data_loaded: self.event_data_loaded = False
        self.events.trigger(f"player.stop")
        
        raise web.HTTPFound('/')
        

    async def handle_default_page(self, request):
        self.logger.debug(f"Serving default, {self.event_data_loaded}")
        # Serve the static HTML file
        if self.event_data_loaded:
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_runner.html")
        else:
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_selector.html")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return web.Response(text=content, content_type="text/html")
        except FileNotFoundError:
            return web.Response(status=404, text="Default page not found")

    async def handle_run_page(self, request):
        self.logger.debug(f"Serving run, {self.event_data_loaded}")
        if self.event_data_loaded:# Serve the static HTML file
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_runner.html")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return web.Response(text=content, content_type="text/html")
            except FileNotFoundError:
                return web.Response(status=404, text="Run page not found")
        else:
            raise web.HTTPFound('/')

    # json reponse for time sync requests from web clients
    async def handle_timesync(self, request):
        data = await request.json()
        try: id = data['id']
        except: id = "null"
        body=json.dumps({"jsonrpc": "2.0", "result": time.time()*1000, "id": f"{id}" })
        return web.Response(
            content_type="application/json", body=body,
        )

    # json reponse for time sync requests from web clients
    async def handle_load_event(self, request):
        self.logger.debug("in handle_load_event")
        data = await request.json()
        self.logger.debug(f"Length of data received: {len(data)}")
        for k in data.keys():
            self.logger.debug(f"  {k}: {data[k]}")
        try:
            
            self.logger.info(f"Handling load_event {data['event']['event_id']}:{data['event']['event_name']}")
            self.events.trigger(f"player.data_available", data)
            self.event_data_loaded = True  
            ## Do some stuff with the data 
        except KeyError:
            return web.Response(status=400, text="Missing 'event' in request")
        else:
            #return web.Response(status=200, text=f"Event load requested")
            raise web.HTTPFound('/run')

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
                          try:
                              r = int(data.get("round", 0))
                              g = int(data.get("group", 0))
                          except ValueError:
                              self.logger.error(f"Bad data for goto: round: {data.get('round', 0)}, group: {data.get('group',0)}")
                          self.events.trigger(f"player.goto", r, g)
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
        site = web.TCPSite(self.runner, "0.0.0.0", 80)
        await site.start()
 
    async def shutdown(self):
        if self.runner:
            await self.runner.cleanup()
    
    def limit_rate(self):
        ## Check how recently we've been called
        ## Reduce rate of updates to max 6 per second
        now = time.time()
        if (now - self.last_update) >= 1/6:
            self.last_update = now
            return False
        else:
            return True

    async def update(self, state):
        # Send the bits of state needed to the web clients
        if (not self.limit_rate()) and state and state.round:
            #msg = json.dumps({"type": "time", "T": state.slot_time, "E": state.end_time, "R": state.round.round_number, "G": state.round.group_number, "N": state.is_no_fly()})
            
            
            d = state.get_dict()
            #self.logger.debug(f"Sending to client: {d}")
            msg = json.dumps(d | {"type": "time"} )
            for ws in list(self.clients):
                #self.logger.debug(f"Sending to client: {msg}")
                try: 
                    await ws.send_str(msg)
                except: #ConnectionResetError ??
                    pass
            
